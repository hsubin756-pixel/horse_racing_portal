package dev.keiba;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.*;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
class PredictServiceTest {
 PredictService.Prediction call(String response) throws Exception {
  return call(response,0);
 }
 PredictService.Prediction call(String response,long delay) throws Exception { return call(response,delay,8L); }
 PredictService.Prediction call(String response,long delay,Long raceId) throws Exception {
  var server=HttpServer.create(new InetSocketAddress("127.0.0.1",0),0);
  server.createContext("/predict",exchange->{
   exchange.getRequestBody().readAllBytes();
   if(delay>0) try {Thread.sleep(delay);} catch(InterruptedException error){Thread.currentThread().interrupt();}
   byte[] bytes=response.getBytes(StandardCharsets.UTF_8);
   exchange.getResponseHeaders().set("Content-Type","application/json");
   exchange.sendResponseHeaders(200,bytes.length);
   try(var output=exchange.getResponseBody()){output.write(bytes);}
  });server.start();
  try {
   var features=mock(PredictionFeatures.class);
   when(features.forRace(8L)).thenReturn(new PredictionFeatures.Input(Map.of(1L,"Horse"),List.of(new PredictService.Features(1L,4,3,1600)),false,null));
   when(features.forRace(9L)).thenReturn(new PredictionFeatures.Input(Map.of(1L,"Horse"),List.of(),true,new PredictService.RealRequest(java.time.LocalDate.of(2022,2,20),1200,List.of(new PredictService.RealHorse(1L,"0044233",56.0,502,11,java.time.LocalDate.of(2019,4,7),"수","안토니오","최용구")))));
   return new PredictService(features,"http://127.0.0.1:"+server.getAddress().getPort()).predict(raceId);
  } finally {server.stop(0);}
 }
 @Test void rejectsMalformedModelResponses() throws Exception {
  for(String body:List.of("{\"modelKind\":\"synthetic_experiment\",\"scores\":[{\"score\":0.5}]}","null","{}","{\"modelKind\":\"other\",\"scores\":[]}",
   "{\"modelKind\":\"synthetic_experiment\",\"scores\":[null]}",
   "{\"modelKind\":\"synthetic_experiment\",\"scores\":[{\"horseId\":1}]}",
   "{\"modelKind\":\"synthetic_experiment\",\"scores\":[{\"horseId\":2,\"score\":0.5}]}",
   "{\"modelKind\":\"synthetic_experiment\",\"scores\":[{\"horseId\":1,\"score\":1.5}]}")) {
   ApiException error=assertThrows(ApiException.class,()->call(body),body);
   assertEquals(503,error.status);
  }
 }
 @Test void timesOutSlowModel() {
  var error=assertThrows(ApiException.class,()->call("{}",4000));assertEquals(503,error.status);
 }
 @Test void realRacesUseTheRealDataEndpointAndCarryModelInfo() throws Exception {
  var ok=call("{\"modelKind\":\"real_data_experiment\",\"cutoffDate\":\"2025-12-28\",\"firstDate\":\"2025-01-04\",\"trainingRaces\":1018,\"holdoutMetrics\":{\"rocAuc\":0.738},\"marketBaselineMetrics\":{\"rocAuc\":0.791},\"scores\":[{\"horseId\":1,\"score\":0.4,\"knownStarts\":3}]}",0,9L);
  assertEquals("real_data_experiment",ok.modelKind());assertEquals(3,ok.scores().getFirst().knownStarts());assertEquals("2025-12-28",ok.info().cutoffDate());assertEquals(0.738,ok.info().holdoutMetrics().get("rocAuc"));assertTrue(ok.disclaimer().contains("시장 정보"));
  for(String body:List.of("{\"modelKind\":\"synthetic_experiment\",\"scores\":[{\"horseId\":1,\"score\":0.4}]}","{\"modelKind\":\"real_data_experiment\",\"scores\":[{\"horseId\":1,\"score\":0.4}]}")) {
   assertEquals(503,assertThrows(ApiException.class,()->call(body,0,9L)).status);
  }
  assertNull(call("{\"modelKind\":\"synthetic_experiment\",\"scores\":[{\"horseId\":1,\"score\":0.25}]}").info());
 }
 @Test void acceptsValidModelResponse() throws Exception {
  assertEquals(0.25,call("{\"modelKind\":\"synthetic_experiment\",\"scores\":[{\"horseId\":1,\"score\":0.25}]}").scores().getFirst().score());
 }
}
