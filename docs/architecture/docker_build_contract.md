# Docker Build 계약

이 문서는 AutoForge가 생성하는 프로젝트의 Docker Build 책임 범위를 정의한다.
`DockerfileGenerator`는 이 계약에 따라 선택적으로 Dockerfile을 생성한다.

## 목적

Docker Build 계약의 목적은 생성된 FastAPI 프로젝트를 동일한 입력으로 재현 가능하게
이미지화할 수 있는 최소 규칙을 정의하는 것이다. 계약은 `ProjectSpec`에서 선택할 수
있는 빌드 설정과 생성 파일의 책임을 연결해야 한다.

## build-only 책임

Dockerfile Generator는 다음만 책임진다.

- 애플리케이션 실행에 필요한 소스와 패키지 설치 단계 정의
- Python 3.12 기반 이미지와 명시적인 실행 명령 정의
- 빌드 컨텍스트에서 생성 프로젝트 외부 경로를 참조하지 않도록 보장
- 이미지 빌드에 필요한 파일을 `GenerationPlan`으로 선언
- 동일한 `ProjectSpec`에 대해 안정적인 Dockerfile 및 보조 파일 생성

다음 작업은 Docker Build Plugin의 책임이 아니다.

- 컨테이너 레지스트리 로그인 또는 이미지 push
- AWS, Kubernetes, ECS 등 배포
- 클라우드 자격 증명, secret, 토큰 생성 및 저장
- 데이터베이스·Redis·RabbitMQ 인프라 프로비저닝
- Git commit, branch, merge 또는 release 생성

## 생성 경계

Docker 파일은 다른 Generator가 소유한 파일을 직접 수정하지 않는다. 파일 충돌은
`GenerationPlan`의 소유권과 manifest 검증으로 탐지해야 한다. Docker 관련 설정이
`ProjectSpec`에 없으면 Docker 생성물은 출력하지 않는 것이 기본값이다.

## 검증 계약

다음 조건을 검증한다.

1. 명세가 비활성화된 경우 Docker 파일이 생성되지 않는지 확인한다.
2. 활성화된 경우 Dockerfile 경로·소유권·명세 해시가 계획에 포함되는지 확인한다.
3. 생성된 Dockerfile에 secret, 배포 명령, 외부 작업 디렉터리 참조가 없는지 확인한다.
4. 프로젝트의 기존 import, pytest, Ruff 검증과 Docker 계약 검증을 분리한다.
5. 실제 이미지 빌드는 Docker가 설치된 환경의 별도 통합 검증으로 둔다.

## 책임 분리

Artifact publishing, deployment, cloud credential 및 Kubernetes·Compose 설정은
Docker build 계약에 포함하지 않고 각 전용 계약에서 정의한다.
