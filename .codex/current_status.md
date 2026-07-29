# 현재 상태

## 완료

- 설정 로딩 기본 구조
- Registry 안정화
- Plugin 기반 클래스와 Metadata
- PluginManager 안정화
- Event와 비동기 EventBus 기본 구조
- Task와 TaskManager 기본 구조
- 기존 테스트의 pytest 마이그레이션
- 전체 테스트 11개 통과 기준선

## 진행 중

- 문서 정합성 정리
- 생성 계약 정의
- 패키지와 코딩 스타일 정리

## 존재하지만 미완성

- CLI 명령
- Plugin Framework
- Pipeline 추상화
- Sample Plugin

PluginLoader는 빈 파일이며 사용되지 않는다. Pipeline은 추상 클래스 자리표시자뿐이므로 Plugin Framework는 아직 완성으로 보지 않는다.

## 시작하지 않음

- ProjectSpec과 GenerationJob
- Workspace와 파일 Manifest
- FastAPI 프로젝트 Generator
- 생성 프로젝트 검증 Pipeline
- Build 및 Git 서비스
- Webhook 서비스
- AI 생성

## 현재 제약

로컬 생성과 검증이 안정되기 전에 Webhook, Git 자동화, AI를 구현하지 않는다. 동작하는 Generator로 확장 계약을 확인하기 전에는 PluginLoader를 구현하지 않는다.