# ADR-0002: 최초 Kubernetes MySQL HA 제공자로 MySQL Operator를 선택한다

## 상태

승인됨. Kubernetes MySQL HA 매니페스트 생성은 아직 구현하지 않았다.

## 맥락

AutoForge의 로컬 MySQL HA 프로필은 MySQL InnoDB Cluster와 MySQL Router를
생성하고, 애플리케이션은 Router writer endpoint를 사용한다. Kubernetes에서도
같은 책임을 직접 StatefulSet, Router Deployment, 초기화 Job으로 재구현하면
업그레이드, 복구, 백업, 상태 조정 책임이 AutoForge에 중복된다.

관리형 MySQL은 초기 운영 부담은 낮지만 제공자별 API와 네트워크 계약을
AutoForge의 기본 Kubernetes 생성기에 고정한다. 반대로 MySQL Operator for
Kubernetes는 InnoDBCluster Custom Resource에서 MySQL Server, Router, Service,
storage Volume과 backup lifecycle을 관리한다.

## 결정

첫 self-hosted Kubernetes MySQL HA 제공자는 **MySQL Operator for Kubernetes**로
선택한다.

- AutoForge는 Operator 설치, CRD 업그레이드, 실제 Secret 값, `kubectl apply`를
  소유하지 않는다.
- 이후의 AutoForge 생성기는 설치된 Operator를 전제로 `InnoDBCluster` 선언과
  애플리케이션의 기존 runtime Secret URL 계약을 생성한다.
- Operator bootstrap Secret과 애플리케이션 runtime Secret은 분리한다. Operator
  관리 계정이나 Router 내부 Secret을 애플리케이션에 재사용하지 않는다.
- 애플리케이션은 Operator가 제공하는 ClusterIP Router Service를 통해 primary에
  연결한다. Kubernetes Service의 공개 MySQL 포트는 `3306`이며 Router 내부
  target port `6446`을 애플리케이션 DSN에 직접 노출하지 않는다.
- MySQL version, TLS Secret, 인스턴스 수, Router replica 수, StorageClass, PVC
  크기, node placement, backup storage와 restore drill은 명세의 필수 provider
  입력으로 둔다. AutoForge는 환경 의존 기본값을 추측하지 않는다.

## 결과

기존 Kubernetes base-server Generator는 Proxy/App/Secret URL binding만 계속
소유한다. MySQL Operator profile이 도입되기 전까지는 MySQL `StatefulSet`이나
Router 리소스를 생성하지 않는다. 이후 profile은 현재 로컬 Compose의
`mysql_mode: ha`와 별도 Kubernetes 명세가 되며, 두 환경의 포트·storage·lifecycle
차이를 숨기지 않는다.

## 근거

- [MySQL Operator 소개](https://dev.mysql.com/doc/mysql-operator/en/mysql-operator-introduction.html)
- [InnoDBCluster 설정과 Volume Claim](https://dev.mysql.com/doc/mysql-operator/en/mysql-operator-innodbcluster-common.html)
- [InnoDBCluster Router Service](https://dev.mysql.com/doc/mysql-operator/en/mysql-operator-innodbcluster-service.html)
- [MySQL Operator backup](https://dev.mysql.com/doc/mysql-operator/en/mysql-operator-backups.html)
