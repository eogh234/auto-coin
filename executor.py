import yfinance as yf
from kis_client import KisClient
from upbit_client import UpbitClient
import time
import datetime
import config

def get_current_price(ticker, market, kis=None):
    """
    현재가를 조달하는 헬퍼 함수 (국내: KIS, 해외/환율: yfinance 활용)
    """
    try:
        if market == 'KR' and kis is not None:
            return kis.get_current_price(ticker)
            
        if market == 'KR':
            yf_ticker = f"{ticker}.KS" 
        else:
            yf_ticker = ticker
            
        data = yf.Ticker(yf_ticker).history(period="1d")
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except Exception as e:
        print(f"가격 조회 실패 ({ticker}): {e}")
    return 0.0

def is_market_open(market='KR'):
    """
    현재 시각이 해당 시장의 정규 운영 시간인지 확인합니다.
    """
    now = datetime.datetime.now()
    # 주말 체크 (5=토요일, 6=일요일)
    if now.weekday() >= 5:
        return False
        
    if market == 'KR':
        # 한국: 09:00 ~ 15:30
        start = now.replace(hour=config.KR_MARKET_OPEN[0], minute=config.KR_MARKET_OPEN[1], second=0, microsecond=0)
        end = now.replace(hour=config.KR_MARKET_CLOSE[0], minute=config.KR_MARKET_CLOSE[1], second=0, microsecond=0)
        return start <= now <= end
    
    # 미국 시장 등 다른 시장은 필요 시 추가 가능 (현재는 KR만 우선 적용)
    return True

def get_current_portfolio_str(kis: KisClient, uc: UpbitClient) -> str:
    """
    에이전트 회의용 현재 포트폴리오 현황 문자열.
    실시간 API 기반: 보유수량 + 현재가 + 평균단가 + 평가손익 + 전체 비중 포함.
    """
    import datetime as _dt

    lines = []
    assets = []   # {'label', 'krw_value', 'detail'}
    total_krw = 0.0

    # 환율 조회 (USD→KRW)
    krw_usd = get_current_price("KRW=X", "US")
    if krw_usd <= 0:
        krw_usd = 1450.0

    # ── 1. 국내 주식 + 예수금 (KIS) ──
    try:
        kr_res = kis.get_balance()
        # 예수금
        kr_out2 = kr_res.get('output2', [{}])
        if isinstance(kr_out2, list):
            kr_out2 = kr_out2[0] if kr_out2 else {}
        kr_cash = float(kr_out2.get('dnca_tot_amt', 0))
        if kr_cash > 0:
            assets.append({'label': '국내 예수금 (투자가능 현금)', 'krw_value': kr_cash,
                           'detail': f'{kr_cash:,.0f}원'})
            total_krw += kr_cash

        # 보유 주식
        for item in kr_res.get('output1', []):
            qty = int(item.get('hldg_qty', '0'))
            if qty <= 0:
                continue
            name       = item.get('prdt_name', '')
            ticker     = item.get('pdno', '')
            cur_price  = float(item.get('prpr', 0))               # 현재가
            avg_price  = float(item.get('pchs_avg_pric', 0))      # 평균단가
            eval_amt   = float(item.get('evlu_amt', 0))           # 평가금액
            pfls_amt   = float(item.get('evlu_pfls_amt', 0))      # 평가손익
            pfls_rt    = float(item.get('evlu_pfls_rt', 0))       # 수익률(%)
            total_krw += eval_amt
            assets.append({
                'label': f'{name} ({ticker}) [KR주식]',
                'krw_value': eval_amt,
                'detail': (f'{qty}주 | 현재가 {cur_price:,.0f}원 | '
                           f'평균단가 {avg_price:,.0f}원 | '
                           f'평가 {eval_amt:,.0f}원 | '
                           f'손익 {pfls_amt:+,.0f}원 ({pfls_rt:+.1f}%)')
            })
    except Exception as e:
        lines.append(f'⚠ 한국 주식 잔고 조회 오류: {e}')

    # ── 2. 미국 주식 (KIS) ──
    try:
        us_res = kis.get_us_balance()
        for item in us_res.get('output1', []):
            qty = float(item.get('ovrs_cblc_qty', item.get('ccld_qty_smic', '0')))
            if qty <= 0:
                continue
            name      = item.get('ovrs_item_name', '')
            ticker    = item.get('ovrs_pdno', '')
            cur_price = float(item.get('now_pric2', 0))           # 현재가 (USD)
            avg_price = float(item.get('pchs_avg_pric', 0))       # 평균단가 (USD)
            eval_usd  = float(item.get('ovrs_stck_evlu_amt', 0))  # 평가금액 (USD)
            pfls_usd  = float(item.get('frcr_evlu_pfls_amt', 0))  # 손익 (USD)
            pfls_rt   = float(item.get('evlu_pfls_rt', 0))        # 수익률(%)
            eval_krw  = eval_usd * krw_usd
            total_krw += eval_krw
            assets.append({
                'label': f'{name} ({ticker}) [US주식]',
                'krw_value': eval_krw,
                'detail': (f'{qty:.0f}주 | 현재가 ${cur_price:.2f} | '
                           f'평균단가 ${avg_price:.2f} | '
                           f'평가 ${eval_usd:.2f} ({eval_krw:,.0f}원) | '
                           f'손익 ${pfls_usd:+.2f} ({pfls_rt:+.2f}%)')
            })
    except Exception as e:
        lines.append(f'⚠ 미국 주식 잔고 조회 오류: {e}')

    # ── 3. 가상자산 (업비트) ──
    try:
        for item in uc.get_all_balances():
            currency = item.get('currency', '')
            qty      = float(item.get('balance', '0'))
            if qty <= 0:
                continue
            if currency == 'KRW':
                if qty >= 100:
                    assets.append({'label': '업비트 KRW 현금 [코인계좌]', 'krw_value': qty,
                                   'detail': f'{qty:,.0f}원'})
                    total_krw += qty
            else:
                ticker_up  = f'KRW-{currency}'
                cur_price  = uc.get_current_price(ticker_up)
                avg_price  = float(item.get('avg_buy_price', 0))
                eval_krw   = qty * cur_price
                pfls_krw   = (cur_price - avg_price) * qty
                pfls_rt    = ((cur_price / avg_price - 1) * 100) if avg_price > 0 else 0
                total_krw += eval_krw
                assets.append({
                    'label': f'{currency} ({ticker_up}) [코인]',
                    'krw_value': eval_krw,
                    'detail': (f'{qty:.4f}개 | 현재가 {cur_price:,.0f}원 | '
                               f'평균단가 {avg_price:,.0f}원 | '
                               f'평가 {eval_krw:,.0f}원 | '
                               f'손익 {pfls_krw:+,.0f}원 ({pfls_rt:+.1f}%)')
                })
    except Exception as e:
        lines.append(f'⚠ 가상자산 잔고 조회 오류: {e}')

    # ── 포맷팅 ──
    now_str = _dt.datetime.now().strftime('%Y-%m-%d %H:%M KST')
    lines.append(f'[현재 포트폴리오] (실시간 기준: {now_str} | 환율: {krw_usd:.1f}원/달러)')
    lines.append(f'총 평가 자산: 약 {total_krw:,.0f}원')
    lines.append('')
    for asset in assets:
        weight = (asset['krw_value'] / total_krw * 100) if total_krw > 0 else 0
        lines.append(f"  [{weight:5.1f}%] {asset['label']}")
        lines.append(f"         {asset['detail']}")

    if not assets:
        lines.append('  (현재 보유 자산 없음 — 전액 현금)')

    return '\n'.join(lines)


def execute_portfolio(kis: KisClient, target_portfolio: list):
    """
    포트폴리오 비중에 맞춰 실제 계좌를 리밸런싱하는 실행 엔진 (Sell First, Buy Later)
    """
    print("\n===========================================")
    print(" ⚙️ [실행 모듈] 주식 포트폴리오 리밸런싱 시작")
    print("===========================================")
    
    # 1. 환율 조회
    krw_usd_rate = get_current_price("KRW=X", "US")
    if krw_usd_rate <= 0:
        krw_usd_rate = 1400.0 # Fallback
    print(f"▶ 적용 환율: {krw_usd_rate:,.2f} 원/달러")

    # 2. 계좌 잔고 조회
    current_holdings = {}
    us_avail_usd = 0.0   # 통합증거금 기준 실제 주문가능 달러(원화 포함)
    try:
        kr_res = kis.get_balance()
        us_res = kis.get_us_balance()

        # ── 국내 잔고 (주식 + 예수금 포함 총평가) ──
        kr_out2 = kr_res.get('output2', [{}])
        if isinstance(kr_out2, list):
            kr_out2 = kr_out2[0] if kr_out2 else {}
        kr_tot_eval_amt = float(kr_out2.get('tot_evlu_amt', 0))   # 국내 총평가 (예수금+주식)
        kr_cash_amt     = float(kr_out2.get('dnca_tot_amt', 0))   # 순수 예수금(KRW)
        kr_stocks_amt   = float(kr_out2.get('scts_evlu_amt', 0))  # 국내 주식 평가금액

        # ── 해외 보유 주식 평가 (USD) ──
        us_out1 = us_res.get('output1', [])
        us_stock_eval_usd = sum(
            float(item.get('ovrs_stck_evlu_amt', 0)) for item in us_out1
        )

        # ── 통합증거금 실제 주문가능금액 조회 (TTTS3007R) ──
        # frcr_ord_psbl_amt1 = 원화 예수금까지 포함한 해외주식 주문가능 USD 환산
        # → 이 값이 실제 미국 주식 BUY 시 사용 가능한 최대 금액
        try:
            import requests as _req
            _token = kis._get_access_token()
            _url = f"{kis.url_base}/uapi/overseas-stock/v1/trading/inquire-psamount"
            _headers = {
                'Content-Type': 'application/json',
                'authorization': f'Bearer {_token}',
                'appKey': kis.app_key,
                'appSecret': kis.app_secret,
                'tr_id': 'TTTS3007R',
                'custtype': 'P'
            }
            _params = {
                'CANO': kis.cano, 'ACNT_PRDT_CD': kis.acnt_prdt_cd,
                'OVRS_EXCG_CD': 'NASD', 'OVRS_ORD_UNPR': '1.00', 'ITEM_CD': 'AAPL'
            }
            _res = _req.get(_url, headers=_headers, params=_params, timeout=5)
            _out = _res.json().get('output', {})
            us_avail_usd = float(_out.get('frcr_ord_psbl_amt1', 0))  # 통합증거금 원화 포함 USD
            print(f"  [통합증거금] 주문가능 USD(원화포함): ${us_avail_usd:,.2f} | 환율: {_out.get('exrt','?')}")
        except Exception as fx_e:
            print(f"  [통합증거금] 주문가능금액 조회 실패: {fx_e}")
            us_avail_usd = kr_cash_amt / krw_usd_rate  # 폴백: 원화 예수금 환산

        # ── 총 운용자산 (국내 총평가 + 해외 보유주식 평가) ──
        total_equity_krw = kr_tot_eval_amt + (us_stock_eval_usd * krw_usd_rate)

        print(f"  [잔고 상세] 국내 예수금: {kr_cash_amt:,.0f}원 | 국내주식: {kr_stocks_amt:,.0f}원 | 해외주식: ${us_stock_eval_usd:,.2f}")
        print(f"  [잔고 요약] 총 운용자산: {total_equity_krw:,.0f}원 | 미국 주문가능: ${us_avail_usd:,.2f}")

        # 현재 보유 수량 매핑 (티커 기준)
        if 'output1' in kr_res:
            for item in kr_res['output1']:
                current_holdings[item.get('pdno')] = {"qty": int(item.get('hldg_qty', '0')), "market": "KR", "name": item.get('prdt_name')}
        for item in us_out1:
            current_holdings[item.get('ovrs_pdno')] = {"qty": float(item.get('ovrs_cblc_qty', item.get('ccld_qty_smic', '0'))), "market": "US", "name": item.get('ovrs_item_name')}

        if total_equity_krw <= 0:
            print("warning: 조회된 주식 잔고가 없습니다. 가상예산 1,000만원 설정.")
            total_equity_krw = 10000000.0

    except Exception as e:
        print(f"warning: 계좌 잔고 조회 오류: {e}. 가상 1,000만원으로 모의 실행.")
        total_equity_krw = 10000000.0

    print(f"▶ 총 추정 증시 자산: {total_equity_krw:,.0f} 원")

    # 3. 목표 수량 파악
    target_quantities = {}
    for asset in target_portfolio:
        ticker = asset.get('ticker')
        weight = asset.get('weight', 0)
        market = asset.get('market', 'KR')
        
        if weight <= 0:
            continue
            
        target_amt_krw = total_equity_krw * (weight / 100.0)
        current_price = get_current_price(ticker, market, kis)
        
        if current_price <= 0:
            print(f"  [-] {asset.get('name')}({ticker}) 가격 조회 실패. 스킵.")
            continue
            
        if market == 'KR':
            target_qty = int(target_amt_krw // current_price)
            order_price = str(int(current_price))
        else: # US Stock
            # 기존 보유 평가액 + 가용 예수금을 합친 총 해외 자산 평가액을 기준으로 비중을 계산하여 매도 후 들어올 자금까지 반영합니다.
            total_us_equity = us_stock_eval_usd + us_avail_usd
            total_us_weight = sum(
                a.get('weight', 0) for a in target_portfolio
                if a.get('market', 'KR') not in ('KR', 'CRYPTO')
            )
            us_ratio = weight / total_us_weight if total_us_weight > 0 else 0
            target_amt_usd = total_us_equity * us_ratio
            target_qty = int(target_amt_usd // current_price)
            order_price = f"{current_price:.2f}"
            print(f"  [US배분] {asset.get('name')}({ticker}): 총해외자산${total_us_equity:.2f} x {us_ratio:.0%} = ${target_amt_usd:.2f}")

        print(f"  [계산] {asset.get('name')}({ticker}): 목표비중 {weight}%, 목표수량 {target_qty}주 (현재가: {current_price})")

            
        target_quantities[ticker] = {
            "qty": target_qty, 
            "price": order_price, 
            "market": market, 
            "name": asset.get('name'),
            "exchange": asset.get('market') if market != 'KR' else "KRX"
        }

    # 4. 차이(Delta) 계산 및 주문 목록 생성
    sell_orders = []
    buy_orders = []
    
    # 4-1. 기존 잔고 기반 파악 (매도/추가매수 필요성)
    for ticker, hold_info in current_holdings.items():
        curr_qty = hold_info['qty']
        target_info = target_quantities.get(ticker)
        
        if target_info is None:
            # 목표 포트폴리오에 없으면 전량 매도
            if curr_qty > 0:
                sell_orders.append({
                    "action": "SELL", "market": hold_info['market'], "ticker": ticker, "name": hold_info['name'],
                    "qty": curr_qty, "price": get_current_price(ticker, hold_info['market'], kis), "exchange": "KRX" if hold_info['market']=='KR' else "NASD"
                })
        else:
            # 목표가 있으면 차이(Delta) 계산
            target_qty = target_info['qty']
            delta = target_qty - curr_qty
            
            if delta < 0:
                sell_orders.append({
                    "action": "SELL", "market": target_info['market'], "ticker": ticker, "name": target_info['name'],
                    "qty": abs(delta), "price": target_info['price'], "exchange": target_info['exchange']
                })
            elif delta > 0:
                buy_orders.append({
                    "action": "BUY", "market": target_info['market'], "ticker": ticker, "name": target_info['name'],
                    "qty": delta, "price": target_info['price'], "exchange": target_info['exchange']
                })

    # 4-2. 기존 잔고에 없었던 신규 종목 매수 추가
    for ticker, target_info in target_quantities.items():
        if ticker not in current_holdings and target_info['qty'] > 0:
            buy_orders.append({
                "action": "BUY", "market": target_info['market'], "ticker": ticker, "name": target_info['name'],
                "qty": target_info['qty'], "price": target_info['price'], "exchange": target_info['exchange']
            })

    # 5. 주문 실행 (매도 우선 → 매수)
    print("\n[주문 실행 로그 - 1단계: 매도]")
    if not sell_orders:
        print("  -> 실행할 주식 매도 주문(Delta)이 없습니다.")
    else:
        for order in sell_orders:
            ticker = order['ticker']
            action = order['action']
            qty    = order['qty']
            price  = order['price']

            if qty <= 0: continue
            try:
                if float(str(price)) == 0.0: continue
            except: pass

            if order['market'] == "KR" and not is_market_open("KR"):
                print(f"  🕒 {order['name']} ({ticker}): 현재 한국 시장 폐장 상태. 매도 스킵.")
                continue

            print(f"  🚀 [SELL] {order['name']} ({ticker}) {qty}주 (예상 단가: {price})")

            # Execute SELL order with retries
            MAX_RETRY = 3
            success = False
            last_msg = ""
            for attempt in range(1, MAX_RETRY + 1):
                try:
                    if order['market'] == "KR":
                        res = kis.sell(ticker=ticker, quantity=qty, order_type="01")
                    else:
                        res = kis.sell_us(ticker=ticker, quantity=qty, price=price, exchange=order['exchange'])
                    last_msg = res.get('msg1', '알 수 없음')
                    is_fail = any(kw in last_msg for kw in ['수량 입력 오류', '시간외'])
                    if not is_fail:
                        print(f"     => API 응답({attempt}회차): {last_msg}")
                        success = True
                        break
                    else:
                        print(f"     => [{attempt}/{MAX_RETRY}] 매도 실패: {last_msg}")
                    if attempt < MAX_RETRY: time.sleep(2)
                except Exception as e:
                    last_msg = str(e)
                    print(f"     => [{attempt}/{MAX_RETRY}] 예외: {last_msg}")
                    if attempt < MAX_RETRY: time.sleep(2)

            if not success:
                print(f"  ❌ [SELL] {order['name']} ({ticker}) 실패: {last_msg}")
            else:
                kis.send_discord_message(f"💸 **[주식 매도 완료]**\n- **종목:** {order['name']} ({ticker})\n- **수량:** {qty}주\n- **결과:** {last_msg}")
            time.sleep(0.5)

    # 5-2. 매도 정산 및 실시간 예수금 재조회 (Plan B/C 가동)
    time.sleep(2)
    real_cash = kr_cash_amt
    real_us_cash = us_avail_usd
    try:
        kr_res = kis.get_balance()
        kr_out2 = kr_res.get('output2', [{}])
        if isinstance(kr_out2, list):
            kr_out2 = kr_out2[0] if kr_out2 else {}
        real_cash = float(kr_out2.get('dnca_tot_amt', 0))

        # 실시간 미국 주문가능달러 재확인
        try:
            import requests as _req
            _token = kis._get_access_token()
            _url = f"{kis.url_base}/uapi/overseas-stock/v1/trading/inquire-psamount"
            _headers = {
                'Content-Type': 'application/json',
                'authorization': f'Bearer {_token}',
                'appKey': kis.app_key, 'appSecret': kis.app_secret,
                'tr_id': 'TTTS3007R', 'custtype': 'P'
            }
            _params = {
                'CANO': kis.cano, 'ACNT_PRDT_CD': kis.acnt_prdt_cd,
                'OVRS_EXCG_CD': 'NASD', 'OVRS_ORD_UNPR': '1.00', 'ITEM_CD': 'AAPL'
            }
            _res = _req.get(_url, headers=_headers, params=_params, timeout=5)
            _out = _res.json().get('output', {})
            real_us_cash = float(_out.get('frcr_ord_psbl_amt1', 0))
        except:
            pass
    except Exception as e:
        print(f"  [잔고 재조회 실패] 기존 잔고 기준으로 매수 진행: {e}")

    # 5-3. 국내 주식 매수 자금 관리 (Plan B/C)
    kr_buys = [o for o in buy_orders if o['market'] == "KR"]
    total_kr_buy_cost = sum(int(o['qty']) * float(o['price']) for o in kr_buys)
    if total_kr_buy_cost > real_cash * 0.995:
        print(f"\n⚠️ [Plan B 가동] 가용 현금({real_cash:,.0f}원)이 국내 매수 소요 자금({total_kr_buy_cost:,.0f}원)보다 부족합니다.")
        print("   비중(목표금액)이 큰 종목 순으로 가용한 범위 내에서 최대한 매수를 할당합니다.")
        kr_buys.sort(key=lambda x: int(x['qty']) * float(x['price']), reverse=True)
        remaining_cash = real_cash * 0.995
        for order in kr_buys:
            price = float(order['price'])
            req_qty = int(order['qty'])
            req_cost = req_qty * price
            if remaining_cash >= req_cost:
                remaining_cash -= req_cost
            else:
                possible_qty = int(remaining_cash // price)
                if possible_qty > 0:
                    print(f"   - {order['name']}: 자금 부족으로 {req_qty}주 ➡️ {possible_qty}주로 축소 (남은현금: {remaining_cash:,.0f}원)")
                    order['qty'] = possible_qty
                    remaining_cash -= possible_qty * price
                else:
                    print(f"   - {order['name']}: 자금 부족으로 매수 취소 (최소 1주 구매 불가, 남은현금: {remaining_cash:,.0f}원)")
                    order['qty'] = 0

    # 5-4. 해외 주식 매수 자금 관리 (Plan B/C)
    us_buys = [o for o in buy_orders if o['market'] != "KR"]
    total_us_buy_cost = sum(int(o['qty']) * float(o['price']) for o in us_buys)
    if total_us_buy_cost > real_us_cash * 0.995:
        print(f"\n⚠️ [Plan B 가동] 가용 달러(${real_us_cash:,.2f})가 해외 매수 소요 자금(${total_us_buy_cost:,.2f})보다 부족합니다.")
        print("   비중(목표금액)이 큰 종목 순으로 가용한 범위 내에서 최대한 매수를 할당합니다.")
        us_buys.sort(key=lambda x: int(x['qty']) * float(x['price']), reverse=True)
        remaining_us_cash = real_us_cash * 0.995
        for order in us_buys:
            price = float(order['price'])
            req_qty = int(order['qty'])
            req_cost = req_qty * price
            if remaining_us_cash >= req_cost:
                remaining_us_cash -= req_cost
            else:
                possible_qty = int(remaining_us_cash // price)
                if possible_qty > 0:
                    print(f"   - {order['name']}: 자금 부족으로 {req_qty}주 ➡️ {possible_qty}주로 축소 (남은달러: ${remaining_us_cash:,.2f})")
                    order['qty'] = possible_qty
                    remaining_us_cash -= possible_qty * price
                else:
                    print(f"   - {order['name']}: 자금 부족으로 매수 취소 (최소 1주 구매 불가, 남은달러: ${remaining_us_cash:,.2f})")
                    order['qty'] = 0

    # 5-5. 매수 주문 실행
    print("\n[주문 실행 로그 - 2단계: 매수]")
    if not buy_orders:
        print("  -> 실행할 주식 매수 주문(Delta)이 없습니다.")
    else:
        for order in buy_orders:
            ticker = order['ticker']
            action = order['action']
            qty    = order['qty']
            price  = order['price']

            if qty <= 0: continue
            try:
                if float(str(price)) == 0.0: continue
            except: pass

            if order['market'] == "KR" and not is_market_open("KR"):
                print(f"  🕒 {order['name']} ({ticker}): 현재 한국 시장 폐장 상태. 매수 스킵.")
                continue

            print(f"  🚀 [BUY] {order['name']} ({ticker}) {qty}주 (예상 단가: {price})")

            # Execute BUY order with retries and limit price fallbacks
            MAX_RETRY = 3
            success = False
            last_msg = ""
            current_order_type = "01"  # 시장가 우선
            LIMIT_PRICE_TRIGGER = ['시장가주문 불가', '시장가호가불가', '기준가 미결정']
            for attempt in range(1, MAX_RETRY + 1):
                try:
                    if order['market'] == "KR":
                        res = kis.buy(ticker=ticker, quantity=qty, order_type=current_order_type)
                    else:
                        res = kis.buy_us(ticker=ticker, quantity=qty, price=price, exchange=order['exchange'])
                    last_msg = res.get('msg1', '알 수 없음')
                    is_fail = any(kw in last_msg for kw in ['수량 입력 오류', '시간외', '시장가주문 불가', '시장가호가불가', '기준가 미결정'])
                    if not is_fail:
                        order_type_label = "지정가" if current_order_type == "00" else "시장가"
                        print(f"     => API 응답({attempt}회차/{order_type_label}): {last_msg}")
                        success = True
                        break
                    else:
                        if any(kw in last_msg for kw in LIMIT_PRICE_TRIGGER) and current_order_type == "01":
                            print(f"     => [{attempt}/{MAX_RETRY}] 시장가 불가 감지 → 지정가(00)로 전환 후 재시도")
                            current_order_type = "00"
                        else:
                            print(f"     => [{attempt}/{MAX_RETRY}] 매수 실패: {last_msg}")
                    if attempt < MAX_RETRY: time.sleep(2)
                except Exception as e:
                    last_msg = str(e)
                    print(f"     => [{attempt}/{MAX_RETRY}] 예외: {last_msg}")
                    if attempt < MAX_RETRY: time.sleep(2)

            if not success:
                print(f"  ❌ [BUY] {order['name']} ({ticker}) 실패: {last_msg}")
                try:
                    kis.send_discord_message(f"🚨 **[매수 최종 실패]**\n- **종목:** {order['name']} ({ticker})\n- **오류:** {last_msg}")
                except: pass
            else:
                kis.send_discord_message(f"💸 **[주식 매수 완료]**\n- **종목:** {order['name']} ({ticker})\n- **수량:** {qty}주\n- **결과:** {last_msg}")
            time.sleep(0.5)

    print("\n✅ 주식 리밸런싱 양방향(BUY/SELL) 실행 완료.")


def execute_crypto(crypto_portfolio: list):
    """
    가상자산 포트폴리오(업비트) 비중에 맞춰 리밸런싱하는 실행 엔진
    """
    print("\n===========================================")
    print(" 🪙 [실행 모듈] 가상자산 리밸런싱 시작")
    print("===========================================")
    
    uc = UpbitClient()
    
    try:
        krw_balance = uc.get_balance("KRW")
        all_bal = uc.get_all_balances()
        
        # 1. 코인 총 계좌 자산 평가 (현금 + 모든 보유코인의 가치합)
        total_crypto_equity = krw_balance
        curr_crypto_holdings = {}
        
        for bal in all_bal:
            currency = bal.get('currency')
            qty = float(bal.get('balance', '0'))
            if currency != "KRW" and qty > 0:
                ticker = f"KRW-{currency}"
                curr_price = uc.get_current_price(ticker)
                curr_value = qty * curr_price
                total_crypto_equity += curr_value
                curr_crypto_holdings[ticker] = {"qty": qty, "curr_val": curr_value, "currency": currency}
                
        if total_crypto_equity <= 0:
            print("⚠️ [업비트 샌드박스] API 반환값이 0입니다. 가상예산 500만원 사용.")
            total_crypto_equity = 5000000.0
    except Exception as e:
        print(f"⚠️ 업비트 계좌 확인 오류: {e}")
        return

    print(f"▶ 총 가상자산 평가 금액: {total_crypto_equity:,.0f} 원")

    sell_orders = []
    buy_orders = []
    target_tickers = set()

    # 2. 매도 (SELL) 로직 도출 (보유 코인 중 비중 초과 또는 리스트 제외분)
    for asset in crypto_portfolio:
        ticker = asset.get('ticker')
        weight = asset.get('weight', 0)
        target_tickers.add(ticker)
        
        target_amt_krw = total_crypto_equity * (weight / 100.0)
        
        if ticker in curr_crypto_holdings:
            curr_val = curr_crypto_holdings[ticker]['curr_val']
            # 목표 금액보다 현재 가치가 크면 그 차액만큼 매도해야 하는데,
            # 업비트의 경우 수량으로 시장가 매도를 날림.
            if curr_val > target_amt_krw:
                sell_amt_krw = curr_val - target_amt_krw
                # 매도할 금액 수량이 너무 작으면(-5000원 등) API에서 튕길 수 있어 패스
                if sell_amt_krw > config.UPBIT_MIN_KRW:
                    sell_ratio = sell_amt_krw / curr_val
                    sell_qty = curr_crypto_holdings[ticker]['qty'] * sell_ratio
                    sell_orders.append((ticker, asset.get('name'), sell_qty, "SELL"))

    # 포트폴리오에 아예 없는데 들고 있는 코인은 전략 매도
    for ticker, info in curr_crypto_holdings.items():
        if ticker not in target_tickers and info['curr_val'] > 5500:
            sell_orders.append((ticker, info['currency']+"(미편입)", info['qty'], "SELL_ALL"))

    # 3. 매도 우선 실행
    for order in sell_orders:
        ticker, name, qty, act = order
        print(f"  🚀 [SELL] {name} ({ticker}) {qty:.4f}개 시장가 매도")
        try:
            res = uc.sell_market_order(ticker, qty)
            print(f"     => 업비트 API 응답: {res}")
            time.sleep(0.3)
        except Exception as e:
            print(f"  ❌ 업비트 매도 실패: {e}")

    # 4. 현금 잔고 갱신 — SELL 체결 완료까지 폴링 대기 (InsufficientFundsBid 방지)
    prev_krw = krw_balance
    new_krw_balance = prev_krw
    if sell_orders:  # 매도 주문이 있었을 때만 대기
        print("  ⏳ 매도 체결 & KRW 정산 대기 중 (최대 30초)...")
        for _ in range(6):  # 5초 × 6 = 최대 30초
            time.sleep(5)
            new_krw_balance = uc.get_balance("KRW")
            if new_krw_balance > prev_krw + 1000:  # 1000원 이상 증가 → 정산 완료로 판단
                print(f"  ✅ KRW 정산 완료: {prev_krw:,.0f}원 → {new_krw_balance:,.0f}원")
                break
        else:
            print(f"  ⚠️ 30초 내 KRW 정산 미확인. 현재 잔고({new_krw_balance:,.0f}원)로 진행.")
    if new_krw_balance == 0 and total_crypto_equity > 0:
        new_krw_balance = total_crypto_equity  # 모의투자용

    # 2. 매수 (BUY) 로직 도출 및 비중 우선순위 정렬
    crypto_buys = []
    for asset in crypto_portfolio:
        ticker = asset.get('ticker')
        weight = asset.get('weight', 0)
        target_amt_krw = total_crypto_equity * (weight / 100.0)
        curr_val = curr_crypto_holdings.get(ticker, {}).get('curr_val', 0)
        if target_amt_krw > curr_val:
            buy_amt = (target_amt_krw - curr_val) * 0.995
            if buy_amt > config.UPBIT_MIN_KRW:
                crypto_buys.append((ticker, asset.get('name'), buy_amt))

    # 비중이 큰 종목 순으로 정렬하여 그리디 자금 할당
    crypto_buys.sort(key=lambda x: x[2], reverse=True)

    for ticker, name, buy_amt_krw in crypto_buys:
        current_krw = uc.get_balance("KRW")
        if current_krw < 5500:
            print(f"  ⚠️ 가용 원화({current_krw:,.0f}원) 부족으로 {name} 매수 스킵.")
            continue

        alloc_krw = min(buy_amt_krw, current_krw * 0.995)
        if alloc_krw >= 5500:
            alloc_krw_int = int(alloc_krw)
            print(f"  🚀 [BUY] {name} ({ticker}) {alloc_krw_int:,.0f}원 어치 시장가 매수")
            try:
                res = uc.buy_market_order(ticker, alloc_krw_int)
                print(f"     => 업비트 API 응답: {res}")
                time.sleep(0.5)
            except Exception as e:
                print(f"  ❌ 업비트 매수 실패: {e}")

    print("\n✅ 가상자산 양방향 리밸런싱 실행 완료.")
