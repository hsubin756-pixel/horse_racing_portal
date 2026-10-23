# 실제 데이터 평가로 전환하는 방법
현재 서비스는 합성 데이터 모델만 제공합니다. 사용 권한이 확인된 경마 결과 데이터가 없으므로 실제 성능을 주장하지 않습니다. SRS에서 제외한 netkeiba 데이터 수집은 구현하지 않았습니다.

사용·저장·분석이 허용되는 다른 데이터 공급자나 직접 보유한 자료를 확보한 뒤, 출처·라이선스·수집 기간을 기록하고 다음 형식의 CSV를 준비합니다. 회원 개인정보나 베팅 계좌 정보는 필요하지 않습니다.

```csv
race_id,race_date,horse_id,distance,finish_position
race-001,2024-01-01,101,1600,1
race-001,2024-01-01,102,1600,2
race-001,2024-01-01,103,1600,3
race-001,2024-01-01,104,1600,4
```

예시는 형식 설명이며 평가에는 서로 다른 개최일이 최소 30일 필요합니다. 경주당 4~100두의 전체 출주 결과와 중복 없는 1~N 착순만 받습니다. 취소·실격·동착 결과를 임의로 바꾸지 말고 별도 정제 규칙을 합의한 뒤 지원을 확장하세요. 경주 ID는 파일 내에서 고유하고 말 ID는 모든 경주에 걸쳐 일관되어야 합니다.

```bash
.runtime/ml-venv/bin/python ml/evaluate.py /secure/path/results.csv \
  --provenance '공급자·허가 근거·자료 기간' \
  --output .runtime/licensed-data-report.json
```

도구는 외부 수집이나 라이선스 판정을 하지 않습니다. 운영자가 선언한 출처와 원본 SHA-256을 보고서에 남깁니다. 앞쪽 80% 개최일로 학습하고 이후 날짜로 평가하며, 같은 날짜의 결과를 입력에 섞지 않습니다. 후기 경주의 입력에는 이미 완료된 이전 날짜 전적을 사용할 수 있습니다. 모델은 고정되어 있으며 홀드아웃 결과를 보고 튜닝하지 않습니다.

Accuracy뿐 아니라 ROC-AUC, average precision(PR 곡선 요약), Brier와 학습 양성 비율 기준 모델, 경주별 상위 3두 recall 및 경주 단위 bootstrap 구간을 계산합니다. 구간은 동일 평가 표본의 재추출 결과이며 미래 성능 보장은 아닙니다. 현재 cold-start 평균 착순 12.5는 API와 같지만 출주 규모 변화에 취약하므로 실제 데이터 분포를 확인하고 함께 개선해야 합니다.

실제 데이터가 확보되면 시간대를 달리한 추가 홀드아웃·여러 기간 검증, 출주 규모별 성능, 확률 보정, 누락/분포 변화, 예측 지연을 평가합니다. 반복 튜닝에는 별도 validation 구간을 두고 최종 test를 남겨야 합니다. 이 도구는 모델을 서비스에 자동 반영하지 않습니다. 현재 합성 모델과 비교하고 검토한 뒤에만 서비스 메타데이터·입력 계약·면책 표시를 함께 변경합니다. 정확도 및 수익 보장은 계속 범위 밖입니다.

## 한국마사회 API155로 실제 데이터 CSV 만들기 — 2026-10-23

승인된 `한국마사회_AI학습용_경주결과`(API155)는 경주일 단위로 출전마별 순위·기록·거리·마번을 제공하므로 위 CSV 계약을 직접 채울 수 있습니다. 이용허락범위 제한 없음(개발계정)으로 평가 실험에는 사용할 수 있으나, 공개 서비스 반영은 운영계정 심의 뒤에 결정합니다.

```bash
python3 scripts/kra_ml_dataset.py collect --meet 1 --from 20250104 --to 20251228 --max-calls 120
python3 scripts/kra_ml_dataset.py export --meet 1 --output .runtime/kra/ml/seoul-2025.csv
.runtime/ml-venv/bin/python ml/evaluate.py .runtime/kra/ml/seoul-2025.csv \
  --provenance '한국마사회 공공데이터포털 API155(AI학습용 경주결과), 개발계정, 2025-01-04~2025-12-28' \
  --output .runtime/kra/ml/report-meet1.json
```

- `collect`는 시행 요일(서울 토·일)만 호출하고 날짜별 원본을 `.runtime/kra/ml/meet-1/`에 보존합니다. 한도에 걸리면 같은 명령을 다음 날 다시 실행해 이어 받습니다. 한 해 서울 자료는 약 105일·호출 210회 안팎입니다.
- `export`는 순위가 1..N으로 완전하고 4두 이상인 경주만 남기고 동착·취소·실격·거리 불일치 경주는 사유별로 제외 건수를 출력합니다. 마번은 선행 0을 제거한 정수, 경주 ID는 `경마장:날짜:경주번호`입니다.
- 평가 결과(JSON)는 합성 모델과 비교해 TEST_REPORT.md에 기록하고, 서비스 모델 교체는 별도 결정입니다. 현재 서비스의 예측은 여전히 합성 실험 모델이며 실제 경주에는 제공하지 않습니다.

### 2025년 서울 자료 평가 결과 (2026-10-23)
97개 개최일·833경주·8,790건으로 위 절차를 실행했습니다. 홀드아웃(2025-10-25~) ROC-AUC 0.686, AP 0.447(양성 비율 0.277), Brier 0.185(기준 0.200), 상위 3두 recall 0.466(95% 0.433~0.498). 세부와 한계는 TEST_REPORT.md에 있습니다. 이 결과는 "실제 데이터로 학습하고 평가한 실험 모델"에 해당하며 서비스에 반영되지 않았습니다.

### 취소마 완화 규칙과 입력 확장 비교 (2026-10-23)
- `export`는 이제 순위가 없는 출전(취소·실격 등)만 제외하고 나머지 순위가 1..N으로 이어지면 경주를 유지합니다(이전에는 경주 전체 제외). 유지한 경주 수를 "(참고)"로 출력합니다. 취소 후 순위에 공백이 생긴 경주는 여전히 제외합니다.
- CSV 뒤쪽에 `jockey, trainer, carried_weight, win_odds, place_odds, gate, horse_weight, rating, sex, birth_date` 열이 붙습니다. 기존 `ml/evaluate.py`는 앞 5열만 읽으므로 그대로 동작합니다.
- `ml/evaluate_extended.py`는 같은 분할·같은 고정 모델로 네 입력 집합(base → +기수/조교사 과거 3위 이내 비율 → +부담중량·마체중·게이트·두수·나이·성별 → +단승 배당)을 비교하고, 모델 없이 배당 순위만으로 고르는 시장 기준선도 함께 냅니다. 기수·조교사 비율은 이전 날짜 결과만 사용합니다. 배당은 마감 후 시장 정보이므로 "시장과 독립적인 예측"으로 제시할 수 없습니다.

```bash
python3 scripts/kra_ml_dataset.py export --meet 1 --output .runtime/kra/ml/seoul-2025.csv
.runtime/ml-venv/bin/python ml/evaluate.py .runtime/kra/ml/seoul-2025.csv --provenance '…' --output .runtime/kra/ml/report-meet1.json
.runtime/ml-venv/bin/python ml/evaluate_extended.py .runtime/kra/ml/seoul-2025.csv --provenance '…' --output .runtime/kra/ml/report-meet1-extended.json
.runtime/ml-venv/bin/python -m unittest ml.test_evaluation_extended   # 또는 cd ml && python -m unittest test_evaluation_extended
```

### 서비스 연결: 실제 데이터 실험 모델 (2026-10-23)
- `ml/train_real.py`가 `ml/data/*.csv`로 시장 정보 없는 입력 집합(base+connections+physical)을 학습해 `real-model.joblib`, `real-history.json`(마번별 착순·기수/조교사별 3위 이내 기록, 학습 마감일까지), `real-model-report.json`(시간순 홀드아웃 지표·시장 기준선)을 만듭니다. Docker 빌드가 `--if-present`로 실행하므로 CSV가 없으면 합성 모델만 제공됩니다.
- FastAPI `POST /predict/real`: Spring이 경주일·거리·출주마의 마번·부담중량·마체중·게이트·생년월일·성별·기수명·조교사명을 보내면, ML 서비스가 **경주일 이전** 보존 이력만으로 입력을 만들어 점수를 냅니다. 모델이 없으면 503.
- Spring `PredictionFeatures`/`PredictService`: `race.source`가 `KRA_`로 시작하면 실제 데이터 모델로, 그 외는 합성 모델로 보냅니다. 응답에 `info`(학습 기간·경주 수·홀드아웃 지표·시장 기준선)와 출주마별 `knownStarts`(보존 전적 수)가 추가됩니다. 예측 화면은 모델 종류에 따라 안내와 지표 표를 다르게 보여 줍니다.
- 한계: 이력은 학습 마감일에 고정되므로 새 결과를 반영하려면 CSV를 갱신하고 이미지를 다시 빌드해야 합니다. 보정·수익성 검증 없음. 서울 1년 자료라 다른 경마장·연도에서의 성능은 확인되지 않았습니다.

데이터 반영 절차:
```bash
cp .runtime/kra/ml/seoul-2025.csv ml/data/seoul-2025.csv   # PROVENANCE.md 의 기간을 맞춰 갱신
./scripts/up.sh                                              # ML 이미지 재빌드 시 train_real.py 실행
curl -s http://127.0.0.1:8000/health                         # realDataModel 에 cutoffDate 가 보이면 준비됨
```
