package dev.keiba;
import java.util.*;
import java.time.Duration;
import java.net.http.HttpClient;
import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.http.client.JdkClientHttpRequestFactory;
@Service
class PredictService {
 final CatalogService catalog; final EntryRepository entries; final RestClient client;
 PredictService(CatalogService c,EntryRepository e,@Value("${app.ml-url}") String url) {
  catalog=c;entries=e;
  var factory=new JdkClientHttpRequestFactory(HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2)).build());factory.setReadTimeout(Duration.ofSeconds(3));
  client=RestClient.builder().baseUrl(url).requestFactory(factory).build();
 }
 record Features(Long horseId,double priorMeanFinish,int starts,int distance) {}
 record MlRequest(List<Features> horses) {}
 record MlScore(Long horseId,double score) {}
 record MlResponse(String modelKind,List<MlScore> scores) {}
 record Score(Long horseId,String horseName,double score) {}
 record Prediction(String modelKind,String disclaimer,List<Score> scores) {}
 @Transactional(readOnly=true) Prediction predict(Long raceId) {
  Race race=catalog.requireRace(raceId);var starters=entries.findByRaceIdOrderByNumberAsc(raceId);
  if(starters.isEmpty()) throw new ApiException(400,"출주마가 없는 경주는 예측할 수 없습니다.");
  var names=new HashMap<Long,String>();var features=new ArrayList<Features>();
  for(Entry entry:starters) {
   var h=catalog.view(entry.horse);names.put(h.id(),h.name());
   var past=entries.past(h.id(),race.raceDate);
   features.add(new Features(h.id(),past.stream().mapToInt(x->x.finishPosition).average().orElse(12.5),past.size(),race.distance));
  }
  try {
   var result=client.post().uri("/predict").body(new MlRequest(features)).retrieve().body(MlResponse.class);
   if(result==null || !"synthetic_experiment".equals(result.modelKind()) || result.scores()==null || result.scores().size()!=names.size()) throw new IllegalArgumentException();
   Set<Long> seen=new HashSet<>();List<Score> scores=new ArrayList<>();
   for(var s:result.scores()) {
    if(!names.containsKey(s.horseId()) || !seen.add(s.horseId()) || !Double.isFinite(s.score()) || s.score()<0 || s.score()>1) throw new IllegalArgumentException();
    scores.add(new Score(s.horseId(),names.get(s.horseId()),s.score()));
   }
   scores.sort(Comparator.comparingDouble(Score::score).reversed().thenComparing(Score::horseId));
   return new Prediction(result.modelKind(),"합성 데이터만으로 학습·평가한 실험 모델입니다. 실제 예측 능력은 검증되지 않았습니다. 점수는 통계적 추정치이며 실제 결과나 수익을 보장하지 않습니다.",scores);
  } catch(RestClientException | IllegalArgumentException ex) { throw new ApiException(503,"예측 서비스를 일시적으로 이용할 수 없습니다. 잠시 후 다시 시도하세요."); }
 }
}
