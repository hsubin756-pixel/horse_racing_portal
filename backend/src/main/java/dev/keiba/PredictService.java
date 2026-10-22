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
 record Score(Long horseId,String horseName,double score) {}
 record Prediction(String modelKind,String disclaimer,List<Score> scores) {}
 Prediction predict(Long raceId) {
  var input=features.forRace(raceId);
  var names=input.names();
  try {
   var result=client.post().uri("/predict").body(new MlRequest(input.horses())).retrieve().body(MlResponse.class);
   if(result==null || !"synthetic_experiment".equals(result.modelKind()) || result.scores()==null || result.scores().size()!=names.size()) throw new IllegalArgumentException();
   Set<Long> seen=new HashSet<>();List<Score> scores=new ArrayList<>();
   for(var s:result.scores()) {
    if(s==null || s.horseId()==null || s.score()==null || !names.containsKey(s.horseId()) || !seen.add(s.horseId()) || !Double.isFinite(s.score()) || s.score()<0 || s.score()>1) throw new IllegalArgumentException();
    scores.add(new Score(s.horseId(),names.get(s.horseId()),s.score()));
   }
   scores.sort(Comparator.comparingDouble(Score::score).reversed().thenComparing(Score::horseId));
   return new Prediction(result.modelKind(),"합성 데이터만으로 학습·평가한 실험 모델입니다. 실제 예측 능력은 검증되지 않았습니다. 점수는 통계적 추정치이며 실제 결과나 수익을 보장하지 않습니다.",scores);
  } catch(RestClientException | IllegalArgumentException ex) { throw new ApiException(503,"예측 서비스를 일시적으로 이용할 수 없습니다. 잠시 후 다시 시도하세요."); }
 }
}
