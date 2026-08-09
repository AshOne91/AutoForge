# KIS HA Kubernetes 참조 청사진

## 목적과 상태

`kis-auto-trading`은 24시간 동작하는 KIS Open API 자동매매 서비스이며, 동시에
AutoForge가 장차 명세에서 생성해야 할 고가용성 웹서비스의 실제 검증 기준이다.

이 문서는 **목표 아키텍처와 생성 경계**를 고정한다. 특정 로컬 Docker 또는 Kubernetes
인스턴스가 현재 실행 중이라는 상태 문서는 아니다. 실행 상태와 검증 결과는 각 환경의
Compose/Kubernetes 명령과 통합 테스트가 판단한다.

## 기준 토폴로지

```text
external client / health probe
  -> king-load-balancer (Kubernetes LoadBalancer, external 8080 -> 80)
  -> instance-web-nginx-deploy (2 replicas, reverse proxy)
  -> backend-service (ClusterIP, 8000)
  -> instance-web-fastapi-deploy (3 stateless replicas)
  -> external state: relational DB, Redis, RabbitMQ
```

각 계층의 책임은 다음과 같이 분리한다.

| 계층 | 책임 | 소유하지 않는 것 |
| --- | --- | --- |
| Load balancer | 외부 진입점과 헬스 프로브 전달 | FastAPI 업무 규칙, KIS 자격 증명 |
| Nginx proxy | 내부 라우팅, 동적 인스턴스 헤더 주입 | 주문·전략·DB 업무 로직 |
| FastAPI app | 무상태 HTTP API, 업무 처리, 외부 상태 Adapter 사용 | 인스턴스별 메모리에 의존한 세션·작업 원장 |
| DB/Redis/RabbitMQ | 업무 원장, 공유 세션·조정, 비동기 전달 | HTTP 라우팅·인증 정책 |

Nginx의 `nginx.conf.template`는 배포 메타데이터를 요청 헤더로 전달할 수 있지만,
그 메타데이터를 업무 분기나 영속 데이터의 기준으로 사용하지 않는다. FastAPI 복제본은
언제든 교체될 수 있으므로 세션과 작업 상태는 외부 저장소에 둔다.

## 저장소와 관측성

개발 기준 구현은 `/app/logs`를 호스트의 `logs/`에 마운트해
`trading_history.log` 같은 실행 영수증을 Pod 수명과 분리한다. 애플리케이션은
unbuffered I/O와 줄 단위 flush를 사용해 충돌 직전의 기록도 남긴다.

이는 로컬·학습 환경의 기준이다. 운영 환경에서는 hostPath에 의존하지 않고 PVC/PV 또는
중앙 로그 수집(Loki/Fluentd 등)으로 교체한다. 이 교체는 로그의 보존 책임을 바꾸지
않으며, 환경 Adapter만 바꾼다.

## Secret 수명주기

Kubernetes manifest와 AutoForge 명세에는 KIS App Key, Secret, 계좌 식별자 같은 실제
자격 증명을 넣지 않는다.

```text
ignored local kis_secret.env
  -> out-of-band kubectl create secret
  -> Kubernetes Secret
  -> secretKeyRef
  -> Pod runtime environment
```

`kis_secret.env`, `*.env`, 로그와 환경 캐시는 Git에서 제외한다. manifest는
`secretKeyRef` 이름과 필요한 key만 참조한다. Secret 생성·회전·삭제는 배포 절차의
명시적인 운영 단계이며, AutoForge의 파일 생성 또는 Git 자동 커밋 단계에 포함하지 않는다.

## AutoForge 생성 경계

이 청사진은 AutoForge가 다음과 같은 **비밀 없는 구조적 산출물**을 생성·검증해야 함을
뜻한다.

### 생성 대상: 배포 가능한 base_server

AutoForge의 제품은 단순 코드 조각이 아니라, 명세 하나에서 조립되는 배포 가능한
`base_server`다. 이 base_server는 Proxy, 무상태 FastAPI App, Service, Probe, Secret
reference, 외부 상태 Adapter와 환경별 storage 선택지를 연결한 최소 실행 단위다.

`kis-auto-trading`은 이 base_server 위에 KIS Broker 연동, 자동매매 전략, 주문과 위험
정책을 올리는 첫 번째 실제 소비자다. 따라서 KIS에만 맞춘 복사본을 AutoForge 안에
보관하지 않는다. 공통 구조는 AutoForge의 Specification과 Generator로 올리고, 금융
업무 규칙은 KIS의 USER_OWNED 영역에 남긴다.

AutoForge의 Control Plane(명세 검증, Generation Job, Git 자동화)은 생성되는
base_server와 다른 애플리케이션이다. 두 역할을 한 서비스·한 배포물로 섞지 않는다.
Control Plane은 base_server를 생성·검증·배포 요청할 수 있지만, 생성 결과의 HTTP
업무 요청을 대신 처리하지 않는다.

- FastAPI application, Router, lifespan, DB/Redis/RabbitMQ Adapter 골격
- Docker build 계약과 `.dockerignore`
- ClusterIP application Service, proxy Deployment/Service, LoadBalancer 또는 Ingress 골격
- replica 수, readiness/liveness probe, ConfigMap template, `secretKeyRef` binding
- 환경별 storage 선택지(hostPath는 로컬 검증 전용, PVC/PV는 운영 전용)
- 생성 파일 Manifest와 실제 환경 검증 명령

AutoForge는 다음을 생성하거나 소유하지 않는다.

- KIS 실제 자격 증명과 계좌 정보
- 자동매매 전략, 주문 정책, 위험 한도
- 실제 cluster에 대한 무승인 `kubectl apply`, Secret 생성, 배포

`kis-auto-trading`은 업무 규칙, KIS 연동 정책, 실제 Secret reference 이름, 운영 배포
정책을 사용자 소유 코드와 운영 절차로 유지한다.

## 확장 순서

1. 현재처럼 무상태 App과 외부 상태 저장소를 먼저 검증한다.
2. Proxy/App/Service/Probe/Secret reference를 명세에서 결정적으로 생성한다.
3. 로컬 hostPath 검증을 PVC/PV 또는 중앙 로그 수집으로 교체한다.
4. LoadBalancer 기반 개발 진입점을 Ingress Controller와 TLS 종료로 확장한다.
5. 전략 신호와 주문 실행 사이의 비동기 전달은 Outbox와 RabbitMQ를 통해 확장한다.

Kubernetes, Redis Cluster, RabbitMQ가 존재한다는 사실만으로 고가용성이 완성되지는
않는다. 각 단계는 장애 시나리오, 재시도·멱등성, 상태 복구를 실제 통합 테스트로
검증한 뒤 다음 단계로 진행한다.
