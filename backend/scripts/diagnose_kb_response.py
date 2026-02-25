"""KB API 응답 필드 진단 스크립트.

KB fastPriceComplexName API 응답에 어떤 필드가 포함되는지 확인.
주소/동 정보가 있으면 매칭 시 pre-filter에 활용 가능.

실행: cd backend && venv/bin/python scripts/diagnose_kb_response.py
"""

import sys
import os
import asyncio
import json
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.WARNING)


async def main():
    from app.crawler.kb_price_client import KBPriceClient, COMPLEX_LIST_URL

    client = KBPriceClient()

    test_cases = [
        ("서울 대치동 (10자리)", "1168010600"),
        ("구리시 인창동 (10자리)", "4131000100"),
        ("구리시 (5자리)", "41310"),
        ("광명시 (5자리)", "41210"),
    ]

    try:
        for label, code in test_cases:
            print(f"\n{'='*60}")
            print(f"  {label}: 법정동코드={code}")
            print(f"{'='*60}")

            await asyncio.sleep(1.5)
            body = await client._request(COMPLEX_LIST_URL, params={"법정동코드": code})

            if not body or not isinstance(body, dict):
                print(f"  응답 없음 (body={body})")
                continue

            data = body.get("data", [])
            result_code = body.get("resultCode", "?")
            result_msg = body.get("resultMessage", "?")

            print(f"  resultCode: {result_code}")
            print(f"  resultMessage: {result_msg}")
            print(f"  data 항목 수: {len(data) if data else 0}")

            if data and len(data) > 0:
                first = data[0]
                print(f"\n  --- 첫 번째 항목의 모든 키 ({len(first.keys())}개) ---")
                for k, v in first.items():
                    print(f"    {k}: {v}")

                # 주소 관련 필드 하이라이트
                print(f"\n  --- 주소 관련 필드 탐색 ---")
                addr_keywords = ["주소", "동", "법정", "지번", "도로", "소재", "시", "구", "읍", "면"]
                for k, v in first.items():
                    if any(kw in k for kw in addr_keywords):
                        print(f"    ★ {k}: {v}")
            else:
                print("  데이터 없음")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
