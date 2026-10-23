# 한국마사회 공공데이터 API 카탈로그 (승인 51건)

2026-10-23 공공데이터포털(data.go.kr)의 각 API 상세 페이지에 내장된 명세(Swagger 또는 요청/출력 표)를 읽어 정리했습니다. 사용자 계정에 **개발계정으로 51건 모두 승인**(만료 2028-10-23)되어 있으며, 인증키는 계정당 하나이므로 `.runtime/kra/service-key`를 그대로 사용합니다. 실제 호출 결과는 사용자 PC에서 확인해야 하며, 아래 항목명은 포털 명세 기준입니다. 필드 수가 많은 API는 핵심 항목만 적었습니다.

공통 규칙: 모든 API는 `https://apis.data.go.kr/B551015/...` 아래의 GET 호출이며 `serviceKey`(또는 `ServiceKey`), `pageNo`, `numOfRows`를 받습니다. 대부분 `_type=json`을 지원하지만 구형 API(표 형식 명세, XML 전용 표기)는 XML만 보장됩니다. 경마장 코드는 보통 1 서울 / 2 제주 / 3 부산경남(영남) / 4 영천이며 API마다 다릅니다(`meet` 또는 `rccrs_cd`). 영천 경주는 부산경남과 합쳐 "영남"으로 표출되는 API가 있습니다.

## 사이트 반영 우선순위

| 순위 | 영역 | API | 사이트 기능 |
|---|---|---|---|
| 1 | 경주마 | 경주마 상세정보(API8_2), 마필종합 상세정보(API42_1), 경주마명단, 말정보 및 개체식별 | 말 상세(모색·생년월일·산지·조교사·마주·부모), 은퇴마 포함 마스터 |
| 1 | 혈통 | 경주마 선대마정보(API47), 혈통정보기본(API284), 씨수말 정보, 교배정보 | 3대(최대 5대) 혈통, 부모 연결 |
| 1 | 인물 | 기수 상세정보(API12_1), 현직기수정보, 기수 성적 정보(API11_1), 조교사 상세정보(API19_1), 통산경주기록 | 기수·조교사 프로필·순위 |
| 1 | 예정 경주 | 경주계획표(racePlan_2), 경주계획정보(API45), AI학습용_경주계획(API154) | 예정 경주·발주 시각·상금, 관심 일정 |
| 2 | 결과 | 경주성적정보(API214_1, 연동됨), 경주기록 정보(API4_3), 경주별상세성적표, 경마시행당일_경주결과종합, 경주 요약성적표, 경마성적정보(API44), 마필경주별 상금정보 | 다른 경마장 결과, 확정 배당(단·연·복·쌍·삼복·삼쌍), 취소/확정 플래그 |
| 2 | 구간 | 경주 구간별 성적 정보(API6_1), 마필 구간별 경주기록(API37_1), 경주마 구간별 통과 누적기록(API46), 경마코너별통과순위_주로빠르기(API303) | 구간 분석·주행 스타일 |
| 2 | 환경 | 경주로정보(API189_1), 경주조건별 최고기록(API32_1) | 주로 상태·함수율, 거리별 최고기록 |
| 3 | ML | AI학습용_경주계획(API154), AI학습용_경주결과, AI기반연구용_경주결과상세(API156) | 실제 데이터 학습·평가 |
| 4 | 상태 | 경마기수변경정보(API48), 출발심사 결과(API21_1), 제재내역(API180_1), 마필 질병 정보(API33) | 기수 교체·취소 사유 |
| — | 보류 | 훈련 5종, 두수 2종, 수출마, 육성마심사, 말 육성정보, 장제정보, 50걸명단, 기간별 비교 2종 | 현재 화면과 무관 |

## 1순위 API 명세

### 경주마 상세정보 — `API8_2/raceHorseInfo_2` (ID 15058115)
요청: `hr_name`, `hr_no`, `meet`(1 서울, 2 제주, 3 영남), `act_gubun`('y' 현역만, 'n' 은퇴 포함, 기본 'y'), `_type`.
응답 item: `hrNo` 마번, `hrName` 마명, `meet`, `name` 출생지, `sex`, `birthday`, `rank` 등급, `rating`, `trName`/`trNo` 조교사, `owName`/`owNo` 마주, `faHrName`/`faHrNo` 부마, `moHrName`/`moHrNo` 모마, `rcCntT`·`ord1CntT`·`ord2CntT`·`ord3CntT` 통산, `rcCntY`·`ord1CntY`·`ord2CntY`·`ord3CntY` 최근 1년, `chaksunT` 통산 상금, `hrLastAmt` 도입가.
비고: 모색은 없음(마필종합 상세정보 사용). 부모 마번이 있어 혈통 연결의 기준이 됩니다.

### 마필종합 상세정보 — `API42_1/totalHorseInfo_1` (ID 15057985)
요청: `hr_eng_name`, `hr_name`, `hr_no`. 셋 다 비우면 임의 100건. 은퇴마 포함.
응답(평면 구조): `hrNo`, `hrNm`, `hrEngNm`, `birthDt`, `sex`, `color` 모색, `age`, `prdCty` 생산국, `expCty` 수입국, `engOrgNm` 원마명, `breed` 품종, `fhrNo`/`fhrNm`/`fhrCty`/`fhrYr` 부마, `mhrNo`/`mhrNm`/`mhrCty`… 모마.
비고: 응답이 `items/item`이 아니라 body 바로 아래 항목일 수 있어 파서에서 두 구조를 모두 처리해야 합니다.

### 경주마 선대마정보 — `API47/rchrBldlnInfo` (ID 15173126)
요청: `hr_no`(필수), `hr_name`, `_type`.
응답: `hrNo`, `hrName`, `meetNm`와 5대 조상 이름 64개. 항목명 규칙 `f1`, `m1`, `f1f2`, `f1m2`, … `m1m2m3m4m5`.
주의: 포털 설명에는 `f1`=모마, `m1`=부마로 적혀 있어 일반적인 f=부/m=모와 반대입니다. 실제 응답을 경주마 상세정보의 `faHrName`/`moHrName`과 대조해 방향을 확정한 뒤 반영해야 합니다. 이름만 제공되고 마번은 없으므로 조상은 이름 기준 말 레코드를 만들고 마번은 비워 둡니다.

### 혈통정보기본 — `API284/HorseBloodBasicInfo` (ID 15109000)
요청: `hrno`, `kor_hrnm`, `foalg_dt_fr/to`, `_type`. 응답: `hrno`, `korHrnm`, `engHrnm`, `foalgDt`, 도시지(Dosage) 지수 7종, 부계/모계 혈통라인 마번·세대수. 혈통 트리에는 선대마정보가 더 직접적이며 이 API는 보조 지표용입니다.

### 씨수말 정보 — `API79_1/stallionInfo_1` (ID 15059488)
요청: 페이지만. 응답: `hrNm`, `hrNo`, `birthDt`, `color`, `regDt`, `prdCty`, `fhrNm`, `mhrNm`, `owNm`, `poNm`. 조상 말의 모색·생년 보강용.

### 교배정보 — `API192/Cross` (ID 15063956, XML)
요청: `cross_date_fr/to`. 응답: 씨암말 `hrNo`/`hrName`, 씨수말 `sireNo`/`sireName`, 자마 `hrNoSon`/`hrNoSonName`, `birthday`, `color`, `sex`, 생산자. 자마-부모 관계의 추가 근거.

### 경주마명단 — `racehorselist/getracehorselist` (ID 15089503, XML)
요청: `meet`, `rank`. 응답: `hrNo`, `hrName`, `nameSp` 소속조, `rank`, `prdCty`, `sex`, `age`, `stDate`, `minRcDate` 데뷔, `jun` 전적 "48(6/12/10)", `prizeYear`, `prizetsum`, `spTerm` 최근 출전, `rating1~4`, `chulYn`. 경마장별 현역마 전체 목록 수집에 적합.

### 말정보 및 개체식별 — `horseinfohi/gethorseinfohi` (ID 15105155)
요청: `hrname`, `hrno`, `reg_dt_fr/to`. 응답: `hrno`, `korHrnm`, `ihrno` 국제마번, `foalgDt`, `gndrNm`, `spcsNm` 품종, `horseCtcolNm` 털색, `pctyNm` 생산국, `sireHrnm`, `damHrnm`, `owrNm`, `sitlNm` 소재지, `ppseNm` 용도, 특징 텍스트, `rchrRegDt`/`rchrRegCnclDt` 경주마 등록·취소일.

### 기수 상세정보 — `API12_1/jockeyInfo_1` (ID 15056828)
요청: `jk_name`, `jk_no`, `meet`. 응답: `jkNo`, `jkName`, `meet`, `part` 소속조, `birthday`(마스킹될 수 있음), `age`, `debut`, `spDate` 은퇴일, `wgPart`/`wgOther` 기승 가능 중량, 통산·최근 1년 출주/1·2·3착.

### 현직기수정보 — `currentjockeyInfo/getcurrentjockeyinfo` (ID 15086329, XML)
기수 상세정보와 같은 항목. 현역만.

### 기수 성적 정보 — `API11_1/jockeyResult_1` (ID 15056591)
요청: `jk_name`, `jk_no`, `meet`(기본 1). 응답: 통산/최근 1년 출주·1·2착, `winRateT`, `qnlRateT`, `winRateY`, `qnlRateY`.

### 조교사 상세정보 — `API19_1/trainerInfo_1` (ID 15057915)
요청: `meet`, `tr_name`, `tr_no`. 응답: `trNo`, `trName`, `meet`, `part`, `birthday`, `age`, `stDate` 데뷔, 통산/최근 1년 출주·1·2·3착, `winRate`/`qnlRate`/`plcRate`(T/Y).

### 마필,기수,조교사 통산경주기록 — `totalRecord_1` (ID 15058399)
요청: `meet`, `pr_gubun`(0 경주마, 1 마주, 2 조교사, 3 기수), `pr_name`, `pr_no`. 응답: 통산/최근 1년/최근 6개월의 출주·1~5위·착순상금·조건상금. 세 종류 프로필을 하나의 호출 형식으로 보강.

### 경주계획표 — `racePlan_2` (ID 15056499, host `B551015/` 직하)
요청: `meet`, `rc_date`, `rc_month`, `rc_year`(모두 생략 시 최근 한 달). 응답: `meet`, `rcDate`, `rcNo`, `ilsu`, `schStTime` 발주 예정 시각, `rcDist`, `rank`, `budam`, `rcName`, `stRating`/`spRating`, `ageCond`, `sexCond`, `chaksun1~5`, `buga1~3`. 출전마 명단은 없음(경주 단위).

### 경주계획정보 — `API45/rcplnInfo` (ID 15173122)
요청: `meet`(필수), `pg_date`(필수). 응답: 경주계획표와 유사 + `rcGrade` 경주격, `rcSeries`, `rcCond`, `newHrCond`, `chaksun1~10`. 영천 포함.

### AI학습용_경주계획 — `API154/racePlan` (ID 15143802)
요청: `rccrs_cd`(필수), `race_dt`(필수), `_type`(필수). 응답: `rccrsNm`, `raceDt`, `raceNo`, `rcgrd`, `raceNm`, `raceDs`, `ptinNhr` 출전두수, `raceClas`, 조건 5종, 상금, `strtPargTm`, `strtTm`, `wetr`, `going`.

### AI학습용_경주결과 — `raceResult` (ID 15143803, host `B551015/` 직하)
요청: `rccrs_cd`, `race_dt`, `_type` 모두 필수. 응답(출전마 단위): `raceDt`, `raceNo`, `raceDs`, `raceNm`, `gtno` 출발번호, `hrno`, `hrnm`, `engHrnm`, `pctyNm`, `bthd`, `gndrNm`, `ratgSo`, `rchrWeg`, `burdWgt`, `jckyNm`, `trarNm`, `ownerNm`, `rk` 순위, `raceRcd` 기록, `margin` 착차, `winPrice` 단승, `placePrice` 연승. 기수·조교사 번호가 없어 이름 매칭 필요.

### AI기반연구용_경주결과상세 — `API156/raceRsutDtl` (ID 15150068)
요청: `rccrs_cd`, `race_dt`, `race_no`, `_type`(필수). 응답: 일정·조건·출전마·관계자(`hrmJckyId`, `hrmTrarId`, `hrmOwnerId`)·결과(`rsutRk`, `rsutRkRemk`, `rsutRkPurse`, `rsutRaceRcd`, `rsutMargin`, `rsutWinPrice`, `rsutQnlaPrice`, `rsutWetr`, `rsutTrckStus`, 실제 출발 시각·변경 사유). ML 학습 표본으로 가장 정보가 많습니다.

## 2순위 이하 요약

- **경주기록 정보 `API4_3/raceResult_3`** (15058305): 경주성적정보(API214_1)와 거의 같은 90개 항목 + 영문명. `plcOdds`가 "복승식"으로 표기되어 있으나 경주 요약성적표에는 `plcOdds`=연승식, `qnlOdds`=복승식으로 구분되므로 **연승식**으로 해석합니다(포털의 경주성적정보 설명도 연승식). 사이트 반영 시 명시.
- **경주별상세성적표 `racedetailresult/getracedetailresult`** (15089492, XML): `meet`·`rc_date` 필수. `win` 단승, `plc` 연승, `hrRating`, `hrTool`, `owCloth`, `chulYn`, 기수/조교사 소속 경마장.
- **경마시행당일_경주결과종합 `Race_Result_total`** (15119524): 94개 항목. `noraceFlag`(0 정상, 1 취소, 2 불성립), `finalBit` 확정 여부, `stTime`/`schStTime`, 기수·조교사 통산/1년 성적 포함. 실시간 제공.
- **경주 요약성적표 `API34_1/raceSummaryResult_1`** (15057579): 단승·연승·복승·쌍승·복연승·삼복승·삼쌍승의 우승 출주번호와 배당률 → 조합별 확정 환급표의 실제 자료원.
- **경마성적정보 `API44/rcpfmcInfo`** (15173120): `meet`·`rc_date` 필수. 착순·착차·누적착차·착순상금·마체중편차·기수감량. 영천 포함.
- **마필경주별 상금정보** (15086325, XML): `meet`, `hr_name`, `rc_date_fr/to`. 착순상금·부가상금.
- **구간 4종**: API6_1(경주 단위 F별 통과거리·통과시간·구간기록·통과순위), API37_1(마필별 구간 최고/최저/평균), API46(부산경남·영천 구간 누적기록, `meet` 3/4만), API303(코너별 순위·3F/4F passtime·주로빠르기 `tempo`).
- **경주로정보 `API189_1/Track_1`** (15063953): `meet`, `rc_date_fr/to`. 기온·습도·풍향·풍속·염도·함수율·주로상태·날씨.
- **경주조건별 최고기록 `API32_1`** (15057344): 거리별 최고기록·평균기록·함수율.
- **상태 4종**: API48 기수변경(`meet`·`rc_date` 필수, 변경 전/후 기수·사유), API21_1 출발심사(`passFlag`, `nopassReason`), API180_1 제재내역(`kind`, `reason`, `fine`, 제재 기간), API33 마필 질병 정보(질병 명칭 사전, 말 단위 아님).
- **보류**: 소속조훈련정보 API49, 언덕주로 훈련, 말훈련내역, 기수일일조교일자, 조교사월별조교비율, 조교사별두수, 마주별두수, 수출마 정보, 육성마심사정보, 말 육성정보, 경주마장제정보, 경주마통산전적50걸명단, 기수기간별성적비교, 조교사기간별전적비교.

## 연동 시 유의점

- 개발계정 일일 트래픽은 API마다 다릅니다(경주마 성적 정보 5, 현직기수정보 3,000 등). 전체 현역마·인물을 수집할 때는 호출 수를 계산하고 원본을 보존해 재호출을 피해야 합니다.
- 일부 API의 `birthday`는 `********`로 마스킹되어 제공됩니다. 비어 있는 값으로 처리하고 추정하지 않습니다.
- 같은 사람·말을 여러 API가 번호(`hrNo`, `jkNo`, `trNo`)로 식별하므로 DB의 `kra_id`를 기준으로 병합하고, 이름만 있는 API(AI학습용_경주결과 등)는 번호가 있는 자료와 대조한 뒤 연결합니다.
- 사용 허가 범위는 "이용허락범위 제한 없음"이나, 운영 배포 시 운영계정 심의가 필요합니다.
