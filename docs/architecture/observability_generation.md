# 관측성(로그) 자동생성 방향

작성일: 2026-08-10

## 목적

AutoForge가 만든 FastAPI 서비스는 먼저 JSON 로그를 stdout과 파일에 남긴다.
이 로그 계약을 유지하면 개발 환경에서는 파일을 ELK로 수집하고, 운영 환경에서는
Filebeat 또는 Fluent Bit 같은 클러스터 수집기로 전환할 수 있다. 애플리케이션은
Elasticsearch나 Kibana를 직접 호출하지 않는다.

흐름은 다음과 같다.

```text
FastAPI / worker
    -> JSON stdout + logs/<service>/*.log
    -> Filebeat filestream (개발 Compose)
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

## 소유권

- AutoForge 생성 파일: 생성기와 명세가 관리한다.
- 서비스별 `LOG_ROOT` 경로와 기본 Compose 파일: 소비자 프로젝트가 관리한다.
- KIS 전용 로그 내용과 도메인 필드: KIS가 관리한다.

생성 결과가 잘못되면 KIS 파일을 직접 고치지 않고 AutoForge 명세·생성기부터 수정한
뒤 KIS를 재생성한다.

## 단계별 진행

1. 현재 단계: 개발용 Compose 오버레이로 파일 로그를 Elasticsearch에 전달하고 Kibana에서 확인한다.
2. 다음 단계: 실제 KIS에서 생성 플래그를 켜고 Compose 병합 검증을 수행한다.
3. 운영 단계: 보안 인증/TLS, Elasticsearch 운영 방식, Kubernetes Filebeat/Fluent Bit
   DaemonSet을 별도 명세와 배포 프로파일로 추가한다.

개발 오버레이는 보안이 꺼져 있고 localhost에만 포트를 열므로 운영에 재사용하지 않는다.
운영 인증·클러스터·DaemonSet은 이번 단계에서 생성하지 않는다.

## 검증 순서

1. ELK Generator 단위 테스트
2. AutoForge 전체 테스트 및 린트
3. KIS에 생성 결과 적용
4. `docker compose config -q`로 기본 Compose와 오버레이 병합 확인
5. 리소스가 허용될 때만 실제 ELK 컨테이너 기동과 로그 수집 확인
