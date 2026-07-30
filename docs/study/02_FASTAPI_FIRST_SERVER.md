# 2권: FastAPI 서버를 손으로 만들기

## 1. FastAPI와 Uvicorn

두 도구의 역할은 다르다.

```text
FastAPI = 어떤 URL에서 어떤 Python 함수를 실행할지 정의
Uvicorn = 네트워크 Port를 열고 요청을 받아 FastAPI에 전달
```

식당으로 비유하면 FastAPI는 메뉴와 조리 규칙이고 Uvicorn은 문을 열고
손님 주문을 받는 직원이다.

## 2. 가장 작은 서버

`main.py`:

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

실행:

```powershell
uvicorn main:app --reload
```

브라우저에서 `http://127.0.0.1:8000/health`를 연다.

```json
{"status": "ok"}
```

## 3. 코드를 한 줄씩 읽기

```python
from fastapi import FastAPI
```

설치된 `fastapi` 패키지에서 `FastAPI` 클래스를 가져온다.

```python
app = FastAPI()
```

FastAPI 클래스의 객체를 만든다. Uvicorn이 실행할 실제 ASGI Application이다.

```python
@app.get("/health")
```

바로 아래 함수를 `GET /health` 요청과 연결하는 Decorator다.

```python
async def health() -> dict[str, str]:
```

- `async def`: 비동기 함수 정의
- `health`: 함수 이름
- `()`: 별도 입력이 없음
- `-> dict[str, str]`: 문자열 Key와 문자열 Value를 가진 Dictionary 반환

```python
return {"status": "ok"}
```

Python Dictionary를 반환한다. FastAPI가 JSON 응답으로 변환한다.

## 4. Path Parameter

```python
@app.get("/orders/{order_id}")
async def get_order(order_id: str) -> dict[str, str]:
    return {"order_id": order_id}
```

`GET /orders/abc`를 호출하면 `order_id`에는 `"abc"`가 들어간다.

## 5. Query Parameter

```python
@app.get("/orders")
async def list_orders(limit: int = 10) -> dict[str, int]:
    return {"limit": limit}
```

`GET /orders?limit=20`을 호출하면 `limit`은 `20`이다. 값을 보내지 않으면
기본값 `10`을 사용한다.

## 6. Pydantic 요청 모델

```python
from pydantic import BaseModel, Field


class CreateOrderRequest(BaseModel):
    symbol: str = Field(min_length=1)
    quantity: int = Field(gt=0)
```

`BaseModel`을 상속하면 Pydantic이 입력을 검사한다.

- `symbol`은 빈 문자열일 수 없다.
- `quantity`는 0보다 커야 한다.

```python
@app.post("/orders")
async def create_order(
    request: CreateOrderRequest,
) -> dict[str, object]:
    return {
        "symbol": request.symbol,
        "quantity": request.quantity,
    }
```

클라이언트가 보낼 JSON:

```json
{
  "symbol": "005930",
  "quantity": 10
}
```

`quantity`가 `-1`이면 함수 실행 전에 FastAPI가 검증 오류 응답을 보낸다.

## 7. 응답 모델

```python
class OrderResponse(BaseModel):
    order_id: str
    symbol: str
    quantity: int
    status: str


@app.post("/orders", response_model=OrderResponse)
async def create_order(
    request: CreateOrderRequest,
) -> OrderResponse:
    return OrderResponse(
        order_id="order-1",
        symbol=request.symbol,
        quantity=request.quantity,
        status="created",
    )
```

응답 모델은 서버가 돌려줄 데이터 형태도 일정하게 만든다.

## 8. Router로 파일 나누기

Endpoint가 많아지면 `main.py` 하나에 모두 넣기 어렵다.

`routers/orders.py`:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/{order_id}")
async def get_order(order_id: str) -> dict[str, str]:
    return {"order_id": order_id}
```

`main.py`:

```python
from fastapi import FastAPI

from routers.orders import router as orders_router

app = FastAPI()
app.include_router(orders_router)
```

`include_router`가 Router의 Endpoint를 Application에 등록한다.

## 9. Application Factory

```python
def create_app() -> FastAPI:
    app = FastAPI(title="KIS Auto Trading")
    app.include_router(orders_router)
    return app


app = create_app()
```

Application 생성 과정을 함수에 모으면 테스트마다 새 App을 만들 수 있고
설정이나 가짜 Service를 주입하기 쉬워진다. AutoForge가 생성하는 서버도 이
방식을 사용한다.

## 10. Service 분리

Router가 모든 업무를 직접 처리하면 코드가 커진다.

```python
class OrderService:
    async def create(
        self,
        request: CreateOrderRequest,
    ) -> OrderResponse:
        return OrderResponse(
            order_id="order-1",
            symbol=request.symbol,
            quantity=request.quantity,
            status="created",
        )
```

Router는 HTTP 입력과 출력에 집중하고 Service는 주문 업무 규칙을 담당한다.

## 11. Depends

```python
from typing import Annotated

from fastapi import Depends


def get_order_service() -> OrderService:
    return OrderService()


@router.post("")
async def create_order(
    request: CreateOrderRequest,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> OrderResponse:
    return await service.create(request)
```

`Depends`는 FastAPI에 “이 Parameter에는 `get_order_service()`의 결과를 넣어
달라”고 요청한다. Router가 전역 Service를 직접 찾지 않게 한다.

## 12. async와 await

DB나 외부 API 응답을 기다리는 동안 CPU는 할 일이 없다.

```python
async def get_account() -> Account:
    account = await repository.find_account()
    return account
```

`await`하는 동안 이벤트 루프는 다른 요청을 처리할 수 있다. CPU 계산 자체가
빨라지는 기능은 아니다.

## 13. lifespan

DB 연결처럼 서버 시작과 종료에 맞춰 관리할 자원이 있다.

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await database.start()
    try:
        yield
    finally:
        await database.stop()
```

- `yield` 전: 서버 시작 준비
- `yield` 후: 서버 종료 정리
- `finally`: 오류가 발생해도 정리

## 14. pytest로 Endpoint 확인

```python
from fastapi.testclient import TestClient


def test_health() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

`assert` 뒤의 조건이 거짓이면 테스트가 실패한다. 실제 Port를 열지 않아도
FastAPI Endpoint를 검사할 수 있다.

## 이번 권에서 기억할 것

```text
Uvicorn은 서버를 실행하고 FastAPI는 요청 처리 규칙을 정의한다.
Decorator가 Method와 Path를 Python 함수에 연결한다.
Pydantic은 요청과 응답 데이터 형태를 검사한다.
Router는 Endpoint를 기능별로 묶는다.
Service는 업무 규칙을 담당한다.
Depends는 필요한 객체를 Handler에 전달한다.
```

다음: [3권: AutoForge 아키텍처](03_AUTOFORGE_ARCHITECTURE.md)

