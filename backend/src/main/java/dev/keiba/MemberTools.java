package dev.keiba;
import java.util.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;

@Service @Transactional
class MemberTools {
 final JdbcTemplate db;final WatchlistService watchlist;
 MemberTools(JdbcTemplate db,WatchlistService watchlist){this.db=db;this.watchlist=watchlist;}
 record Note(Long id,Long horseId,Long raceId,String body,String tags,Long revision){}
 List<Map<String,Object>> notes(long user,String q){if(q.length()>100)throw new ApiException(400,"검색어는 100자 이하로 입력하세요.");return db.queryForList("SELECT n.*,h.name horse_name,r.name race_name FROM personal_note n LEFT JOIN horse h ON h.id=n.horse_id LEFT JOIN race r ON r.id=n.race_id WHERE n.member_id=? AND (LOCATE(?,n.body)>0 OR LOCATE(?,n.tags)>0) ORDER BY n.updated_at DESC,n.id DESC LIMIT 200",user,q,q);}
 Object save(long user,Note note){
  if((note.horseId()==null)==(note.raceId()==null)||note.body()==null||note.body().isBlank()||note.body().length()>2000||note.tags()==null||note.tags().length()>200)throw new ApiException(400,"대상 하나와 메모(1~2000자), 태그(200자 이하)를 입력하세요.");
  String target=note.horseId()!=null?"horse":"race";long targetId=note.horseId()!=null?note.horseId():note.raceId();
  if(db.queryForObject("SELECT COUNT(*) FROM "+target+" WHERE id=?",Long.class,targetId)!=1)throw new ApiException(404,"메모 대상을 찾을 수 없습니다.");
  if(note.id()==null){db.update("INSERT INTO personal_note(member_id,horse_id,race_id,body,tags) VALUES (?,?,?,?,?)",user,note.horseId(),note.raceId(),note.body().strip(),note.tags().strip());}
  else if(note.revision()==null||db.update("UPDATE personal_note SET body=?,tags=?,updated_at=CURRENT_TIMESTAMP(6),revision=revision+1 WHERE id=? AND member_id=? AND revision=? AND "+(note.horseId()!=null?"horse_id":"race_id")+"=?",note.body().strip(),note.tags().strip(),note.id(),user,note.revision(),targetId)!=1)throw new ApiException(409,"메모를 다시 불러온 뒤 수정하세요.");
  return Map.of("saved",true);
 }
 void delete(long user,long id){db.update("DELETE FROM personal_note WHERE id=? AND member_id=?",id,user);}
 Object notifications(long user){
  // Explicit refresh on opening the inbox. No background delivery is claimed.
  var schedule=watchlist.schedule(user);
  for(var row:schedule.races())if(!row.race().raceDate().isAfter(schedule.asOfDate().plusDays(7))){
   db.update("INSERT INTO site_notification(member_id,race_id,race_date,message) VALUES (?,?,?,?) ON DUPLICATE KEY UPDATE message=VALUES(message)",user,row.race().id(),row.race().raceDate(),row.race().name()+" · "+row.race().raceDate()+" 관심 대상의 출전 예정 경주입니다.");
  }
  return db.queryForList("SELECT n.*,r.status race_status FROM site_notification n JOIN race r ON r.id=n.race_id WHERE n.member_id=? ORDER BY n.created_at DESC,n.id DESC LIMIT 100",user);
 }
 void read(long user,long id){db.update("UPDATE site_notification SET is_read=TRUE WHERE id=? AND member_id=?",id,user);}
}
@RestController @RequestMapping("/api")
class MemberToolsController {
 final MemberTools service;MemberToolsController(MemberTools service){this.service=service;}
 @GetMapping("/notes") Object notes(@AuthenticationPrincipal Long user,@RequestParam(defaultValue="") String q){return service.notes(user,q);}
 @PostMapping("/notes") Object save(@AuthenticationPrincipal Long user,@RequestBody MemberTools.Note note){return service.save(user,note);}
 @DeleteMapping("/notes/{id}") @ResponseStatus(org.springframework.http.HttpStatus.NO_CONTENT) void delete(@AuthenticationPrincipal Long user,@PathVariable long id){service.delete(user,id);}
 @PostMapping("/notifications/refresh") Object refresh(@AuthenticationPrincipal Long user){return service.notifications(user);}
 @PostMapping("/notifications/{id}/read") @ResponseStatus(org.springframework.http.HttpStatus.NO_CONTENT) void read(@AuthenticationPrincipal Long user,@PathVariable long id){service.read(user,id);}
}
