# 그랜드슬램 2026

Python과 Pygame으로 만든 3이닝 타격 게임입니다.

## 실행

Python 3.13과 Pygame 2.6.1 환경에서 검증했습니다. 게임 창을 표시할 수 있는 데스크톱 환경이 필요합니다.

프로젝트 폴더에서 다음 명령을 실행하세요.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 Grandslam2026.py
```

Windows에서는 `python3` 대신 `py`를 사용하고, 가상환경은 PowerShell에서 `.venv\Scripts\Activate.ps1`로 활성화합니다.

## 조작

| 입력 | 동작 |
| --- | --- |
| Enter | 게임 시작 / 다음 투구 시작 |
| 마우스 이동 | 배트 조준 |
| Space | 스윙 (투구 대기 중에는 투구 시작) |
| Esc | 종료 |

공이 타석 가까이 도착했을 때 스윙하세요. 한 투구에는 한 번만 스윙할 수 있습니다.

## 구현된 기능

- 1280×900 타석 시점 경기장, 베이스별 주자 표시
- 내야수 4명·외야수 3명 및 주자 유무에 따른 수비 위치 조정
- 직구·슬라이더·커브와 투구 원근 효과, 잔상, 도착 지점의 구종 표시
- 180도 어퍼스윙 모션과 배트의 원근 효과
- 내야를 직선으로 통과하는 땅볼 1루타, 외야 앞에 떨어지는 뜬공 1루타
- 외야 사이로 향하는 포물선 2루타, 좌우 구석으로 향하는 포물선 3루타
- 홈런·뜬공·땅볼 타구 애니메이션
- 볼넷, 삼진, 병살, 진루·득점 및 3이닝 종료 처리

스윙 후에도 투구는 원래 도착점까지 진행합니다. 타구가 발생하면 애니메이션 종료 후 결과를 반영합니다. 타구 결과는 배트 접촉 부위에 따른 확률로 결정하며, 수비수 추적이나 포구 동작은 구현하지 않았습니다.

## 변경 사항 관리

GitHub 연결을 마친 뒤 코드를 수정하면 다음 순서로 기록합니다.

```bash
git diff
git add Grandslam2026.py README.md requirements.txt .gitignore
git commit -m "변경한 내용을 간단히 설명"
git push
```

`git commit`은 로컬에 변경 기록을 저장하고, `git push`는 GitHub에 전송합니다.

## 한글 폰트

게임 화면의 버튼, 점수판, 조작 안내와 결과 메시지는 한글로 표시합니다. 포지션 표기와 구종 이름은 영문으로 유지합니다. 모든 글자는 프로젝트에 포함된 나눔고딕 폰트로 표시합니다. 다른 컴퓨터에서도 `assets/fonts` 폴더를 함께 유지하세요.

폰트 출처: [Google Fonts의 Nanum Gothic](https://github.com/google/fonts/tree/main/ofl/nanumgothic). 폰트에는 SIL Open Font License 1.1이 적용되며, 전문은 [assets/fonts/OFL.txt](assets/fonts/OFL.txt)에 있습니다. 이 라이선스는 포함된 폰트에 적용됩니다.
