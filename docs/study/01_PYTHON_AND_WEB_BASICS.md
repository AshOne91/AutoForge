# 1권: Python과 웹 기초

## 1. 프로그램이란 무엇인가

프로그램은 컴퓨터가 순서대로 실행할 명령의 모음이다.

```python
price = 1000
quantity = 3
total = price * quantity
print(total)
```

컴퓨터는 다음 순서로 처리한다.

1. `price`라는 이름에 숫자 `1000`을 저장한다.
2. `quantity`에 `3`을 저장한다.
3. 두 값을 곱해 `total`에 저장한다.
4. `total`을 화면에 출력한다.

`=`는 수학의 “같다”보다 “오른쪽 값을 왼쪽 이름에 저장한다”에 가깝다.

## 2. 값과 타입

데이터에는 종류가 있다.

```python
name = "AutoForge"       # str: 문자열
version = 1              # int: 정수
price = 10.5             # float: 소수
enabled = True           # bool: 참 또는 거짓
modules = ["account"]    # list: 여러 값을 순서대로 보관
```

타입은 컴퓨터가 값을 어떻게 다뤄야 하는지 알려 준다. `"10"`은 글자이고
`10`은 숫자다.

```python
"10" + "20"  # "1020"
10 + 20      # 30
```

## 3. 함수

함수는 여러 명령에 이름을 붙여 재사용하는 방법이다.

```python
def calculate_total(price: int, quantity: int) -> int:
    total = price * quantity
    return total
```

한 부분씩 읽는다.

- `def`: 함수를 정의한다.
- `calculate_total`: 함수 이름이다.
- `price`, `quantity`: 함수가 받을 입력이다.
- `: int`: 정수를 기대한다는 타입 힌트다.
- `-> int`: 정수를 반환할 예정이라는 뜻이다.
- `return`: 계산 결과를 호출한 곳으로 돌려준다.

호출:

```python
result = calculate_total(1000, 3)
```

`result`에는 `3000`이 저장된다.

## 4. 클래스와 객체

클래스는 데이터와 기능을 함께 묶는 설계도다.

```python
class Order:
    def __init__(self, symbol: str, quantity: int) -> None:
        self.symbol = symbol
        self.quantity = quantity

    def total(self, price: int) -> int:
        return price * self.quantity
```

객체는 그 설계도로 만든 실제 값이다.

```python
order = Order("005930", 10)
amount = order.total(70000)
```

```text
Order  = 주문 객체의 설계도
order  = 실제로 만든 주문 객체
```

`self`는 지금 사용 중인 객체 자신을 뜻한다.

## 5. 모듈과 패키지

Python 파일 하나가 모듈이다.

```text
calculator.py
```

다른 파일에서 가져올 수 있다.

```python
from calculator import calculate_total
```

여러 모듈을 폴더로 묶은 것이 패키지다.

```text
trading/
├── __init__.py
├── orders.py
└── accounts.py
```

```python
from trading.orders import Order
```

AutoForge의 `package_name`이 `kis_auto_trading`처럼 Python 이름이어야 하는
이유가 이것이다. `kis-auto-trading`의 하이픈은 빼기 연산자로 해석될 수 있어
일반적인 import 이름으로 사용할 수 없다.

## 6. 프로그램과 서버의 차이

일반 프로그램은 일을 마치면 종료된다.

```text
실행 → 계산 → 결과 출력 → 종료
```

서버는 보통 계속 실행되면서 요청을 기다린다.

```text
서버 시작
  → 요청 기다림
  → 요청 처리
  → 응답
  → 다시 요청 기다림
```

웹서버는 웹의 통신 규칙인 HTTP로 요청과 응답을 주고받는 서버다.

## 7. 클라이언트와 서버

요청하는 쪽이 클라이언트이고 요청을 처리하는 쪽이 서버다.

```text
브라우저 또는 앱                 FastAPI 서버
      │                              │
      │ GET /health 요청             │
      ├─────────────────────────────►│
      │                              │ 상태 확인
      │ 200 OK, {"status": "ok"}     │
      │◄─────────────────────────────┤
```

브라우저만 클라이언트인 것은 아니다. 모바일 앱, 다른 서버와 테스트 코드도
클라이언트가 될 수 있다.

## 8. HTTP 요청

HTTP 요청에는 주로 다음 정보가 있다.

```text
Method: GET
Path: /orders/123
Headers: 부가 정보
Body: 전송할 데이터
```

자주 쓰는 Method:

| Method | 일반적인 의미 |
|---|---|
| GET | 데이터 조회 |
| POST | 데이터 생성 또는 명령 실행 |
| PUT | 전체 변경 |
| PATCH | 일부 변경 |
| DELETE | 삭제 |

Method의 의미는 약속이다. GET이라고 해서 데이터 변경이 물리적으로 불가능한
것은 아니지만, 그렇게 작성하면 사용자와 도구가 동작을 예측하기 어려워진다.

## 9. HTTP 응답

응답에는 상태 코드와 데이터가 있다.

```text
Status: 200 OK
Content-Type: application/json

{"order_id": "123", "status": "created"}
```

대표 상태 코드:

| 코드 | 뜻 |
|---|---|
| 200 | 요청 성공 |
| 201 | 새 데이터 생성 성공 |
| 400 | 요청 내용이 잘못됨 |
| 404 | 대상을 찾지 못함 |
| 422 | 입력 데이터 검증 실패 |
| 500 | 서버 내부 오류 |

## 10. JSON

JSON은 프로그램 사이에서 데이터를 주고받을 때 많이 사용하는 텍스트 형식이다.

```json
{
  "symbol": "005930",
  "quantity": 10,
  "market_order": false
}
```

Python Dictionary와 비슷하지만 완전히 같은 문법은 아니다.

```python
order = {
    "symbol": "005930",
    "quantity": 10,
    "market_order": False,
}
```

JSON은 `false`, Python은 `False`를 사용한다.

## 11. API와 Endpoint

API는 다른 프로그램이 기능을 사용할 수 있도록 공개한 입구다. Endpoint는
HTTP Method와 URL Path를 합친 구체적인 입구다.

```text
GET  /health       서버 상태 조회 Endpoint
POST /orders       주문 생성 Endpoint
GET  /orders/123   123번 주문 조회 Endpoint
```

## 이번 권에서 기억할 것

```text
함수는 입력을 받아 일을 하고 결과를 반환한다.
클래스는 객체를 만들기 위한 설계도다.
웹서버는 HTTP 요청을 기다렸다가 응답한다.
API Endpoint는 Method와 Path로 구분되는 기능의 입구다.
JSON은 클라이언트와 서버가 데이터를 주고받는 형식이다.
```

다음: [2권: FastAPI 서버를 손으로 만들기](02_FASTAPI_FIRST_SERVER.md)

