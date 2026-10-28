package dev.keiba;

import com.fasterxml.jackson.databind.*;
import java.nio.file.*;
import java.io.IOException;
import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

@RestController
class KraStatusController {
 final CatalogAdmin admin; final ObjectMapper json; final Path directory; final JdbcTemplate db;
 KraStatusController(CatalogAdmin admin,ObjectMapper json,JdbcTemplate db,@Value("${KRA_SYNC_DIR:.runtime/kra/sync/dashboard}") String directory){
  this.admin=admin;this.json=json;this.db=db;this.directory=Path.of(directory);
 }
 @GetMapping("/api/admin/kra-status")
 Map<String,Object> status(@AuthenticationPrincipal Long user){
  admin.authorize(user);
  var jobs=new ArrayList<Map<String,Object>>();int unreadable=0;boolean limited=false;
  if(Files.isDirectory(directory)){
   try(var paths=Files.list(directory)){
    var candidates=paths.filter(p->p.getFileName().toString().matches("[0-9]{8}-[0-9]{8}-[123]{1,3}\\.json"))
     .sorted(Comparator.reverseOrder()).limit(101).toList();limited=candidates.size()>100;
    for(var path:candidates.stream().limit(100).toList()){
     try{
      if(Files.isSymbolicLink(path)||Files.size(path)>16*1024*1024)throw new IOException();
      var state=json.readTree(Files.readString(path));
      if(state==null||!state.path("tasks").isObject())throw new IOException();
      jobs.add(summarize(path.getFileName().toString().replace(".json",""),state));
     }catch(IOException|RuntimeException e){unreadable++;}
    }
   }catch(IOException e){unreadable++;}
  }
  var database=db.queryForMap("SELECT COUNT(*) races,COALESCE(SUM(status='VOID'),0) voidRaces,MIN(race_date) firstDate,MAX(race_date) lastDate FROM race WHERE source='KRA_API214_1'");
  database.put("lastImportedAt",db.queryForObject("SELECT MAX(imported_at) FROM kra_race_import",java.sql.Timestamp.class));
  return Map.of("jobs",jobs,"database",database,"unreadableFiles",unreadable,"limited",limited,
   "note","진행표는 마지막 실행 기록입니다. 기간별 작업은 겹칠 수 있으며 DB 반영 수와 별도로 표시합니다.");
 }
 static Map<String,Object> summarize(String id,JsonNode state){
  var issues=new ArrayList<Map<String,String>>();int site=0,training=0,held=0,imported=0;
  var tasks=state.path("tasks").fields();
  while(tasks.hasNext()){
   var item=tasks.next();if(!item.getKey().matches("[123]:[0-9]{8}"))continue;
   var task=item.getValue();
   if(Set.of("반영 완료","자료 없음").contains(task.path("site").asText()))site++;
   if("수집 완료".equals(task.path("training").asText()))training++;
   for(String stage:List.of("site","training"))if(task.hasNonNull(stage+"_error"))
    issues.add(Map.of("task",item.getKey(),"race","","reason",safeError(task.path(stage+"_error").asText())));
   var races=task.path("races").fields();
   while(races.hasNext()){
    var race=races.next();if(!race.getKey().matches("[0-9]{1,2}"))continue;
    if("반영 완료".equals(race.getValue().path("status").asText()))imported++;
    if(race.getValue().hasNonNull("error")){
     held++;if(issues.size()<1000)issues.add(Map.of("task",item.getKey(),"race",race.getKey(),"reason",safeError(race.getValue().path("error").asText())));
    }
   }
  }
  return Map.of("id",id,"updatedAt",state.path("updatedAt").asText(""),"tasks",state.path("tasks").size(),
    "siteCompleted",site,"trainingCompleted",training,"importedRaces",imported,"heldRaces",held,
    "calls",state.path("calls").asLong(0),"issues",issues);
 }
 static String safeError(String text){
  // Never send local paths, URLs, or arbitrary provider values to the dashboard.
  if(text.contains("/")||text.contains("\\")||text.length()>300)return "상세 사유는 로컬 상태 조회에서 확인하세요.";
  return text.replaceAll("[\\p{Cntrl}]", " ");
 }
}
