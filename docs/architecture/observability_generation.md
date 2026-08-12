# 관측성(로그) 자동생성 방향

## 목적

AutoForge가 만든 FastAPI 서비스는 먼저 JSON 로그를 stdout과 파일에 남긴다.
이 로그 계약을 유지하면 개발 환경에서는 파일을 ELK로 수집하고, 운영 환경에서는
Filebeat 또는 Fluent Bit 같은 클러스터 수집기로 전환할 수 있다. 애플리케이션은
Elasticsearch나 Kibana를 직접 호출하지 않는다.

흐름은 다음과 같다.

```text
FastAPI / worker
    -> JSON stdout + logs/*.log or logs/<service>/*.log
    -> Filebeat filestream + persistent read registry (개발 Compose)
    -> Elasticsearch
    -> Kibana
```

## 생성 진입점

`tooling.elk.enabled`가 `true`일 때만 ELK Generator가 다음 파일을 만든다.

- `deploy/observability/compose.elk.yaml`: Elasticsearch, Kibana, Filebeat 오버레이
- `deploy/observability/filebeat.yml`: 애플리케이션 JSON-lines 수집 규칙
- `deploy/observability/README.md`: 실행법과 안전 경계

기본값은 꺼져 있다. 따라서 ELK 이미지를 사용하지 않는 프로젝트에는 추가 컨테이너,
볼륨, 포트가 생기지 않는다.

`tooling.elk.mode`는 두 배포 형태를 구분한다.

- `central`(기본값): Elasticsearch, Kibana, Filebeat를 한 개발 Compose 프로젝트에서 실행한다.
- `collector`: 해당 애플리케이션 인스턴스에는 Filebeat만 실행하고, `ELASTICSEARCH_HOST`
  환경변수로 중앙 Elasticsearch 주소를 주입한다.

따라서 여러 인스턴스는 각각 `collector` 오버레이를 설치할 수 있고, 중앙 ELK는 한 번만
운영할 수 있다. 인스턴스별 수집기는 애플리케이션 로그 디렉터리만 읽으며 Elasticsearch
데이터 볼륨을 소유하지 않는다.

## 소유권

- AutoForge 생성 파일: 생성기와 명세가 관리한다.
- 서비스별 `LOG_ROOT` 경로와 기본 Compose 파일: 소비자 프로젝트가 관리한다.
- KIS 전용 로그 내용과 도메인 필드: KIS가 관리한다.

생성 결과가 잘못되면 KIS 파일을 직접 고치지 않고 AutoForge 명세·생성기부터 수정한
뒤 KIS를 재생성한다.

## Runtime boundaries

Generated JSON logging allowlists durable-job event type, job type, job ID, run
key, current attempt, and maximum attempts for safe operational filtering.

- `central` 모드는 로컬 개발용 Elasticsearch, Kibana와 Filebeat를 생성한다.
- `collector` 모드는 Filebeat만 생성하고 Elasticsearch 주소를 환경 변수로 받는다.
- `tooling.elk.kubernetes_collector_enabled`는 Filebeat ConfigMap과 DaemonSet만
  생성하며 중앙 Elasticsearch나 credential을 생성하지 않는다.
- 운영 환경의 TLS, 인증, 중앙 저장소와 collector 리소스 정책은 생성물 밖의
  배포 책임이다.

개발 오버레이는 보안이 꺼져 있고 localhost에만 포트를 열므로 운영에 재사용하지 않는다.
Kubernetes collector는 Elasticsearch/Kibana를 만들지 않으며, Secret에 TLS endpoint와
최소 권한 API 키가 준비된 뒤에만 적용한다.

## 검증 계약

1. ELK Generator 단위 테스트
2. AutoForge 전체 테스트 및 린트
3. KIS에 생성 결과 적용
4. `docker compose config -q`로 기본 Compose와 오버레이 병합 확인
5. 리소스가 허용될 때만 실제 ELK 컨테이너 기동과 로그 수집 확인
