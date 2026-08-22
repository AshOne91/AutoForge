# ADR-0005: KIS 증권계좌는 사용자가 소유하고 자격 증명은 배포 Secret에서 해석한다

## Status

Accepted as the boundary required before KIS portfolio persistence or order work.

## Context

KIS의 현재 `KisDomesticAccountClient`는 `KIS_ACCOUNT_*` 환경변수에서 하나의
계좌를 읽고, 내부 operator service token으로 보호된 조회 경로에서 실시간
보유종목만 반환한다. 이 계좌는 배포 설정에 속하며 로그인한 AutoForge 사용자와
연결되어 있지 않다.

반면 KIS 로그인 식별정보는 Global `identity` 저장소에 `user_id`와 `shard_id`를
보관하고, 프로필과 알림 같은 사용자 데이터는 `user_id`로 분할된 Account Shard에
저장한다. 참고 Base Server도 로그인 세션의 사용자 키와 샤드 ID로 계좌와
포트폴리오를 같은 사용자 샤드에 배치한다. 그 구조는 소유권과 샤드 배치에 대한
좋은 계보이지만, 실제 계좌번호를 샤드 테이블에 평문으로 저장한 방식까지 복사할
수는 없다.

## Decision

1. 증권계좌 연결 메타데이터는 KIS 소비자 도메인인
   `BrokerageAccountConnection`이 소유한다. 각 연결은 정확히 한 `user_id`에
   속하고 그 사용자의 Account Shard에 저장한다.
2. Global `LoginAccount`는 계속 로그인 식별자, 접근 등급, 샤드 배치만 소유한다.
   증권계좌 메타데이터나 KIS 자격 증명을 Global 저장소에 추가하지 않는다.
3. 연결 레코드에는 `connection_id`, `user_id`, provider, 실행 환경, 표시 이름,
   마스킹된 계좌 식별자, 상태, 불투명한 `credential_ref` 같은 비밀이 아닌
   메타데이터만 저장한다.
4. App Key, App Secret, 전체 계좌번호와 상품 코드는 명세, 데이터베이스,
   Outbox/Inbox payload, 로그에 저장하지 않는다. 런타임 resolver가
   `credential_ref`를 배포 Secret으로 해석하며, 알 수 없는 참조는 fail closed로
   거부한다.
5. 첫 구현은 기존 환경변수 묶음을 가리키는 단 하나의 참조
   `kis:default`만 지원한다. 배포 설정의 `KIS_ACCOUNT_OWNER_USER_ID`가 이 참조를
   연결할 수 있는 단 한 명의 로그인 사용자를 지정하며, 값이 없거나 세션 사용자와
   다르면 연결을 fail closed로 거부한다. 실제 두 번째 자격 증명 공급자가 생기기
   전에는 범용 broker factory나 Secret Manager 추상화를 만들지 않는다.
6. 사용자 요청은 인증 세션에서 `user_id`와 `shard_id`를 얻고, 그 샤드의 연결
   레코드를 읽은 다음 자격 증명을 해석한다. 비동기 작업과 메시지는 사용자 및
   연결 식별자만 운반하며 실제 자격 증명을 운반하지 않는다.
7. 현재 operator 보유종목 조회는 배포 계정 연결을 진단하는 read-only 경로로
   남는다. 사용자 포트폴리오의 source of truth로 간주하지 않는다.
8. 공용 시장 데이터는 계속 Global `automation` 저장소에 둔다. 향후 보유자산
   snapshot, 주문, 체결, risk 및 감사 이력은 사용자와 계좌 연결에 귀속되므로
   Account Shard에 둔다.

## Consequences

로그인 사용자와 외부 증권계좌 사이의 소유권이 명시되고, 샤드 확장과 배포 Secret
교체가 서로 독립적이 된다. 데이터베이스 유출만으로 실제 KIS 호출에 필요한
자격 증명을 복원할 수 없다.

첫 구현은 한 배포 Secret 묶음만 해석하므로 다중 증권사나 사용자별 Secret
Manager 저장소를 제공하지 않는다. 이 ADR은 포트폴리오 snapshot 주기, stale-data
정책, 주문 멱등성, 체결 조정, risk 규칙을 결정하지 않는다. 각 기능은 계좌 연결
수직 슬라이스가 실제로 검증된 뒤 별도 결정으로 진행한다.

## Rejected alternatives

- 배포 계정의 포트폴리오를 Global 저장소에 저장: 사용자 소유권과 샤드 격리를
  잃으므로 거부한다.
- KIS App Secret과 전체 계좌번호를 Account Shard에 암호화해 저장: 현재는 키 관리
  수명주기가 없고 기존 배포 Secret이면 충분하므로 보류한다.
- 구현 전에 범용 multi-broker credential 계층 생성: 두 번째 실제 소비자 요구가
  없으므로 보류한다.

## References

- [KIS HA reference blueprint](../reference/kis_ha_reference_blueprint.md)
- [Reference project strategy](../reference/reference_project_strategy.md)
- [Database generation](../architecture/database_generation.md)
