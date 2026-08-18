# ADR-0003: Control Plane의 첫 Kubernetes 제공자로 Kubernetes-native 리소스를 선택한다

## 상태

승인됨. Control Plane Kubernetes 매니페스트 생성은 아직 구현하지 않았다.

## 맥락

AutoForge의 Control Plane은 PostgreSQL에 Job과 service heartbeat를 저장한다.
로컬 Docker profile은 검증됐지만, AWS·GKE·AKS처럼 특정 클라우드 제공자를 지금
생성기에 고정하면 Secret, 네트워크, 데이터베이스 운영 계약이 제품의 범용 명세가
아닌 제공자별 API에 묶인다. 반대로 PostgreSQL StatefulSet을 AutoForge가 직접
생성하면 데이터베이스의 백업·복구·업그레이드 책임도 중복해서 소유하게 된다.

현재 `/health`는 process liveness만 의미한다. PostgreSQL 연결 가능성을 확인하는
readiness 계약 없이 이를 Kubernetes readiness probe로 재사용하면, 저장소에 연결할
수 없는 Control Plane으로 요청이 라우팅될 수 있다.

## 결정

첫 Control Plane Kubernetes 제공자는 **Kubernetes-native**로 선택한다.

- 향후 profile은 표준 `Deployment`, 내부 `ClusterIP` `Service`, 그리고 미리 생성된
  opaque `Secret`만 생성한다.
- Secret은 `AUTOFORGE_DATABASE_URL`과 `AUTOFORGE_CONTROL_PLANE_TOKEN`을 runtime
  environment로 바인딩한다. 실제 Secret 값과 생성·회전은 배포 제공자가 소유한다.
- PostgreSQL은 provider-owned 외부 의존성이다. Control Plane generator는
  PostgreSQL `StatefulSet`, PVC, migration Job, backup 또는 restore policy를 만들지
  않는다.
- `/health`는 liveness에만 사용한다. DB-aware readiness endpoint와 migration
  operating contract가 구현되기 전에는 Control Plane Kubernetes manifest를 생성하지
  않는다.
- Control Plane Service는 기본적으로 cluster-internal이다. 외부 synthetic probe는
  Control Plane을 공용으로 노출시키기 위해 만들지 않으며, 기존 규칙대로 소비자
  애플리케이션의 public request path를 검증한다.

## 결과

Docker Desktop, EKS, GKE, AKS 및 self-managed Kubernetes에서 같은 generated
runtime contract를 사용할 수 있다. 클라우드별 Ingress, Secret manager, PostgreSQL
제공자, image registry, multi-zone placement와 backup 정책은 이후 provider adapter가
선택될 때 추가한다. 이 결정은 application routing/restart authority를 heartbeat가
아닌 Kubernetes pull probe에 남긴다.

## 근거

- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Kubernetes liveness, readiness, startup probes](https://kubernetes.io/docs/concepts/workloads/pods/probes/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
