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
 PredictService.Prediction call(String response,long delay) throws Exception {
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
   when(features.forRace(8L)).thenReturn(new PredictionFeatures.Input(Map.of(1L,"Horse"),List.of(new PredictService.Features(1L,4,3,1600))));
   return new PredictService(features,"http://127.0.0.1:"+server.getAddress().getPort()).predict(8L);
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
 @Test void acceptsValidModelResponse() throws Exception {
  assertEquals(0.25,call("{\"modelKind\":\"synthetic_experiment\",\"scores\":[{\"horseId\":1,\"score\":0.25}]}").scores().getFirst().score());
 }
}
