# 영상 컨트롤타워

모든 제작 채팅방(Claude Code 세션)이 만든 영상을 `tower.db` 한 곳에서 관리한다.

## 실행 (Windows)
Python 3가 설치돼 있어야 한다. `control-tower` 폴더의 `시작.bat`을 더블클릭하면 DB 생성 + 서버 실행 + 브라우저가 열린다. 창을 닫으면 서버가 꺼진다.

## 구조
채널(구글계정+유튜브 채널) → 제작방(source, 업로드 시각) → 영상(video)

| 채널 | 제작방 | 종류 | 업로드 시각 |
|---|---|---|---|
| 모든 쇼핑 (taejung) | 시니어쇼츠-GPT | 쇼츠 | 22:15 |
| 모든 쇼핑 (taejung) | 정치-fork3 | 쇼츠 | 10:15 |
| 시선각도 (temxo0678) | 롱폼운세-띠별 | 롱폼 | 17:15 |
| 시선각도 (temxo0678) | 운세숏폼-수진당시선각도 | 쇼츠 | 10:15 |
| 시선각도 (temxo0678) | 시니어쇼츠-초반어그로 | 쇼츠 | 22:15 |
| 작두별상대신 수진당 (missnoble0070) | 롱폼운세-날짜별 | 롱폼 | 17:45 |
| 작두별상대신 수진당 (missnoble0070) | 운세숏폼-수진당시선각도@작두별상대신 수진당 | 쇼츠 | 11:15 |

## 제작 세션(각 채팅방)이 지킬 규칙
영상이 완성될 때마다 DB에 등록한다. 제목·썸네일 경로는 필수.
```bash
python tower.py add --source "<제작방 이름>" --title "<제목>" --file "<영상 절대경로>" --thumbnail "<썸네일 절대경로>" --description "<설명>" --tags "<태그>"
```
이미 만든 영상도 같은 명령으로 한 번씩 등록한다. 같은 제작방·같은 파일은 덮어쓴다.

## 운영
```bash
python tower.py init                         # DB 생성(최초 1회)
python tower.py schedule                     # 대기 영상을 제작방별 업로드 시각에 맞춰 하루 1편씩 배정
python tower.py interval --channel "시선각도" --hours 6   # 채널 단위로 6시간 간격 분배(마지막 업로드 기준)
python tower.py list                         # 전체 현황
python tower.py done <id> --url <영상URL>    # 업로드 완료 처리
python tower.py serve                        # 대시보드 http://localhost:8765
```
대시보드: 채널·제작방별 목록, 상태(대기/예약/완료), "제목 복사", "업로드 페이지 열기"(YouTube Studio), "완료 처리".

## 자동 업로드는 아직 미구현
현재는 스케줄 *배정*과 수동 업로드 보조까지다. 자동 업로드 방식은 택일 필요:
1. YouTube Data API(계정 3개 OAuth) + 내 PC에서 상시 실행 → PC가 켜져 있어야 함
2. Uplika 같은 예약 게시 서비스(서버가 예약 시각에 게시) → PC 꺼져도 됨
3. 지금처럼 대시보드로 수동 업로드
