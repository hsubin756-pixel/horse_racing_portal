package dev.keiba;
import java.util.*;
import java.time.Duration;
import java.net.http.HttpClient;
import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.http.client.JdkClientHttpRequestFactory;
@Service
class PredictService {
 final PredictionFeatures features; final RestClient client;
 PredictService(PredictionFeatures features,@Value("${app.ml-url}") String url) {
  this.features=features;
  var factory=new JdkClientHttpRequestFactory(HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2)).build());factory.setReadTimeout(Duration.ofSeconds(3));
  client=RestClient.builder().baseUrl(url).requestFactory(factory).build();
 }
 record Features(Long horseId,double priorMeanFinish,int starts,int distance) {}
 record MlRequest(List<Features> horses) {}
 record MlScore(Long horseId,Double score) {}
 record MlResponse(String modelKind,List<MlScore> scores) {}
 record RealHorse(Long horseId,String kraId,Double carriedWeight,Integer bodyWeight,Integer gate,java.time.LocalDate birthDate,String sex,String jockey,String trainer) {}
 record RealRequest(java.time.LocalDate raceDate,int distance,List<RealHorse> horses) {}
 record RealScore(Long horseId,Double score,Integer knownStarts) {}
 record RealResponse(String modelKind,String cutoffDate,String firstDate,Integer trainingRaces,Map<String,Object> holdoutMetrics,Map<String,Object> marketBaselineMetrics,List<RealScore> scores) {}
 record Score(Long horseId,String horseName,double score,Integer knownStarts) {}
 /** info: 실제 데이터 모델의 학습 기간·홀드아웃 지표·시장 기준선. 합성 모델은 null. */
 record ModelInfo(String firstDate,String cutoffDate,Integer trainingRaces,Map<String,Object> holdoutMetrics,Map<String,Object> marketBaselineMetrics) {}
 record Prediction(String modelKind,String disclaimer,List<Score> scores,ModelInfo info) {}
 static final String SYNTHETIC_DISCLAIMER="합성 데이터만으로 학습·평가한 실험 모델입니다. 실제 예측 능력은 검증되지 않았습니다. 점수는 통계적 추정치이며 실제 결과나 수익을 보장하지 않습니다.";
 static final String REAL_DISCLAIMER="한국마사회 공개 자료로 학습한 실험 모델입니다. 배당 등 시장 정보는 입력에 넣지 않았고, 학습 기간 이후의 전적은 재학습 전까지 반영되지 않습니다. 점수는 입상 확률이 아니며 실제 결과나 수익을 보장하지 않습니다.";
 Prediction predict(Long raceId) {
  var input=features.forRace(raceId);
  var names=input.names();
  try {
   if(input.real()) {
    var result=client.post().uri("/predict/real").body(input.realRequest()).retrieve().body(RealResponse.class);
    if(result==null || !"real_data_experiment".equals(result.modelKind()) || result.scores()==null || result.scores().size()!=names.size() || result.cutoffDate()==null) throw new IllegalArgumentException();
    Set<Long> seen=new HashSet<>();List<Score> scores=new ArrayList<>();
    for(var s:result.scores()) {
     if(s==null || s.horseId()==null || s.score()==null || !names.containsKey(s.horseId()) || !seen.add(s.horseId()) || !Double.isFinite(s.score()) || s.score()<0 || s.score()>1) throw new IllegalArgumentException();
     scores.add(new Score(s.horseId(),names.get(s.horseId()),s.score(),s.knownStarts()));
    }
    scores.sort(Comparator.comparingDouble(Score::score).reversed().thenComparing(Score::horseId));
    return new Prediction(result.modelKind(),REAL_DISCLAIMER,scores,new ModelInfo(result.firstDate(),result.cutoffDate(),result.trainingRaces(),result.holdoutMetrics(),result.marketBaselineMetrics()));
   }
   var result=client.post().uri("/predict").body(new MlRequest(input.horses())).retrieve().body(MlResponse.class);
   if(result==null || !"synthetic_experiment".equals(result.modelKind()) || result.scores()==null || result.scores().size()!=names.size()) throw new IllegalArgumentException();
   Set<Long> seen=new HashSet<>();List<Score> scores=new ArrayList<>();
   for(var s:result.scores()) {
    if(s==null || s.horseId()==null || s.score()==null || !names.containsKey(s.horseId()) || !seen.add(s.horseId()) || !Double.isFinite(s.score()) || s.score()<0 || s.score()>1) throw new IllegalArgumentException();
    scores.add(new Score(s.horseId(),names.get(s.horseId()),s.score(),null));
   }
   scores.sort(Comparator.comparingDouble(Score::score).reversed().thenComparing(Score::horseId));
   return new Prediction(result.modelKind(),SYNTHETIC_DISCLAIMER,scores,null);
  } catch(org.springframework.web.client.HttpServerErrorException.ServiceUnavailable ex) {
   throw new ApiException(503,input.real()?"실제 데이터 모델이 아직 준비되지 않았습니다. ml/data 에 자료를 두고 서비스를 다시 빌드하세요.":"예측 서비스를 일시적으로 이용할 수 없습니다. 잠시 후 다시 시도하세요.");
  } catch(RestClientException | IllegalArgumentException ex) { throw new ApiException(503,"예측 서비스를 일시적으로 이용할 수 없습니다. 잠시 후 다시 시도하세요."); }
 }
}
