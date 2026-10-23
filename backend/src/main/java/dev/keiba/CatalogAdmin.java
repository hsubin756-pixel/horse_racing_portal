package dev.keiba;
import java.util.*;
import java.time.*;
import java.math.BigDecimal;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;

@Service @Transactional
class CatalogAdmin {
 final JdbcTemplate db;final ObjectMapper json;
 CatalogAdmin(JdbcTemplate db,ObjectMapper json){this.db=db;this.json=json;}
 // All identifiers originate here, never from a request.
 static final Map<String,String> TABLES=Map.of("horses","horse","races","race","entries","entry","sectionals","sectional","payouts","payout","people","person");
 static final Map<String,String> FIELDS=Map.of(
  "horses","name,sex,birth_date,color,trainer,trainer_id,sire_id,dam_id",
  "races","name,race_date,start_time,venue,distance,surface,race_class,weather,going,status,source",
  "entries","race_id,horse_id,number,jockey,jockey_id,gate,carried_weight,body_weight,weight_change,status,finish_position,time_seconds,popularity_rank,win_odds,odds_source,odds_as_of",
  "sectionals","entry_id,distance,position,cumulative_seconds,source",
  "payouts","race_id,market,combination,status,odds,amount_yen,source,as_of",
  "people","kind,name,biography,source");
 void authorize(Long user){if(user==null||!Boolean.TRUE.equals(db.queryForObject("SELECT is_admin FROM member WHERE id=?",Boolean.class,user)))throw new ApiException(403,"관리자 권한이 필요합니다.");}
 String table(String kind){if(kind==null)bad("자료 종류");String t=TABLES.get(kind);if(t==null)throw new ApiException(400,"자료 종류를 확인하세요.");return t;}
 List<Map<String,Object>> list(Long user,String kind,int page){authorize(user);if(page<0||page>10000)bad("페이지");return db.queryForList("SELECT * FROM "+table(kind)+" ORDER BY id DESC LIMIT 50 OFFSET ?",page*50);}
 List<Map<String,Object>> audit(Long user){authorize(user);return db.queryForList("SELECT * FROM catalog_audit ORDER BY id DESC LIMIT 100");}
 void remove(Long user,String kind,long id,long revision){
  authorize(user);if(!Set.of("sectionals","payouts").contains(kind))bad("삭제 가능한 자료 종류");
  db.queryForList("SELECT id FROM member WHERE is_admin=TRUE ORDER BY id FOR UPDATE");
  var rows=db.queryForList("SELECT * FROM "+table(kind)+" WHERE id=? FOR UPDATE",id);
  if(rows.isEmpty())throw new ApiException(404,"삭제할 자료가 없습니다.");var before=rows.getFirst();
  if(n(before,"revision")!=revision)throw new ApiException(409,"다른 변경이 있습니다. 자료를 다시 불러오세요.");
  db.update("DELETE FROM "+table(kind)+" WHERE id=?",id);
  try{db.update("INSERT INTO catalog_audit(member_id,kind,record_id,before_json,after_json) VALUES (?,?,?,?,?)",user,kind,id,json.writeValueAsString(before),"{\"deleted\":true}");}catch(com.fasterxml.jackson.core.JsonProcessingException e){throw new IllegalStateException(e);}
 }
 record Batch(List<Map<String,Object>> rows){}
 record Csv(String csv){}
 static void bad(String name){throw new ApiException(400,name+" 입력값을 확인하세요.");}
 static long number(Object value){try{return new BigDecimal(value.toString()).longValueExact();}catch(Exception e){bad("정수");return 0;}}
 static BigDecimal decimal(Object value){try{return new BigDecimal(value.toString());}catch(Exception e){bad("숫자");return null;}}
 static String str(Map<String,Object> row,String key){return Objects.toString(row.get(key),"");}
 static long n(Map<String,Object> row,String key){return row.get(key)==null?0:number(row.get(key));}
 static void required(Map<String,Object> row,String...fields){for(String f:fields)if(row.get(f)==null||str(row,f).isBlank())bad(f+" 필수");}
 static void choice(Map<String,Object> row,String key,String...values){if(!Set.of(values).contains(str(row,key)))bad(key);}
 static void range(Map<String,Object> row,String key,double lo,double hi){if(row.get(key)!=null){double d=decimal(row.get(key)).doubleValue();if(d<lo||d>hi)bad(key);}}
 void ref(Map<String,Object> row,String key,String table){if(row.get(key)!=null&&db.queryForObject("SELECT COUNT(*) FROM "+table+" WHERE id=?",Long.class,row.get(key))!=1)bad(key+" 참조");}
 Map<String,Object> normalize(String kind,Map<String,Object> raw){
  if(raw==null)bad("빈 행");table(kind);var allowed=new HashSet<>(List.of(FIELDS.get(kind).split(",")));allowed.addAll(List.of("id","revision"));
  if(!allowed.containsAll(raw.keySet()))bad("지원하지 않는 열");
  var row=new LinkedHashMap<String,Object>();
  for(String key:allowed){Object value=raw.get(key);if(value instanceof String s)value=s.strip().isEmpty()?null:s.strip();
   if(value!=null){
    if(Set.of("id","revision","trainer_id","sire_id","dam_id","race_id","horse_id","jockey_id","entry_id","number","gate","body_weight","weight_change","finish_position","popularity_rank","distance","position","amount_yen").contains(key))value=number(value);
    else if(Set.of("carried_weight","time_seconds","win_odds","cumulative_seconds","odds").contains(key)){BigDecimal v=decimal(value);int scale=Set.of("time_seconds","cumulative_seconds").contains(key)?2:1;if(v.scale()>scale)bad(key+" 소수 자릿수");value=v;}
    else {String s=value.toString();int max=key.equals("biography")?2000:key.equals("name")&&kind.equals("races")?150:Set.of("source","odds_source").contains(key)?120:100;if(s.length()>max)bad(key+" 길이");value=s;}
   }row.put(key,value);
  }
  if(n(row,"id")<0||n(row,"revision")<0)bad("ID/버전");
  if(n(row,"id")>0&&row.get("revision")==null)bad("수정 버전");
  for(String key:List.of("birth_date","race_date"))if(row.get(key)!=null)try{LocalDate d=LocalDate.parse(str(row,key));if(d.getYear()<1800||d.getYear()>2200)bad(key);}catch(java.time.DateTimeException e){bad(key);}
  if(row.get("start_time")!=null)try{LocalTime.parse(str(row,"start_time"));}catch(Exception e){bad("발주 시각");}
  for(String key:List.of("as_of","odds_as_of"))if(row.get(key)!=null)try{row.put(key,java.sql.Timestamp.from(Instant.parse(str(row,key))));}catch(Exception e){bad(key+" UTC 시각(예: 2026-10-23T03:00:00Z)");}
  switch(kind){
   case "horses"->{required(row,"name","sex","birth_date","color","trainer");choice(row,"sex","수","암","거");ref(row,"trainer_id","person");ref(row,"sire_id","horse");ref(row,"dam_id","horse");person(row,"trainer_id","TRAINER","trainer");for(String f:List.of("sire_id","dam_id"))if(n(row,f)>0&&n(row,f)==n(row,"id"))bad("자기 자신을 부모로 지정할 수 없습니다");}
   case "races"->{required(row,"name","race_date","venue","distance","surface","status","source");range(row,"distance",400,10000);choice(row,"surface","잔디","더트","장애");choice(row,"status","SCHEDULED","RUNNING","OFFICIAL","CANCELLED");for(String f:List.of("race_class","weather","going"))if(str(row,f).length()>(f.equals("race_class")?60:30))bad(f);}
   case "entries"->{required(row,"race_id","horse_id","number","jockey","status");ref(row,"race_id","race");ref(row,"horse_id","horse");ref(row,"jockey_id","person");person(row,"jockey_id","JOCKEY","jockey");range(row,"number",1,30);range(row,"gate",1,30);range(row,"carried_weight",30,80);range(row,"body_weight",200,800);range(row,"weight_change",-100,100);range(row,"finish_position",1,30);range(row,"time_seconds",1,9999);range(row,"popularity_rank",1,30);range(row,"win_odds",1,999999);choice(row,"status","DECLARED","FINISHED","SCRATCHED","DNF","DISQUALIFIED");
    if(str(row,"status").equals("FINISHED"))required(row,"finish_position");else if(row.get("finish_position")!=null)bad("미완주/미출전 말의 착순");
    if(Set.of("DECLARED","SCRATCHED").contains(str(row,"status"))&&row.get("time_seconds")!=null)bad("미출전 말의 기록");
    long supplied=List.of("popularity_rank","win_odds","odds_source","odds_as_of").stream().filter(f->row.get(f)!=null).count();if(supplied!=0&&supplied!=4)bad("인기/배당/출처/시각은 함께 입력");
   }
   case "sectionals"->{required(row,"entry_id","distance","source");ref(row,"entry_id","entry");range(row,"distance",1,10000);range(row,"position",1,30);range(row,"cumulative_seconds",.01,99999);if(row.get("position")==null&&row.get("cumulative_seconds")==null)bad("순위 또는 누적 시간");}
   case "payouts"->{required(row,"race_id","market","combination","status","source","as_of");ref(row,"race_id","race");choice(row,"market","WIN","PLACE","QUINELLA","EXACTA","TRIO","TRIFECTA");choice(row,"status","OPEN","FINAL","REFUND");
    String[] parts=str(row,"combination").split("-",-1);int count=switch(str(row,"market")){case "WIN","PLACE"->1;case "QUINELLA","EXACTA"->2;default->3;};if(parts.length!=count)bad("조합 수");
    List<Integer> ns=new ArrayList<>();for(String p:parts){long num=number(p);if(num<1||num>30)bad("조합 마번");ns.add((int)num);}if(new HashSet<>(ns).size()!=count)bad("중복 마번");if(Set.of("QUINELLA","TRIO").contains(str(row,"market")))Collections.sort(ns);row.put("combination",String.join("-",ns.stream().map(Object::toString).toList()));
    if(str(row,"status").equals("OPEN")){required(row,"odds");range(row,"odds",1,999999999);if(row.get("amount_yen")!=null)bad("예상 배당의 확정 환급금");}
    else{required(row,"amount_yen");range(row,"amount_yen",100,1000000000);if(row.get("odds")!=null||str(row,"status").equals("REFUND")&&n(row,"amount_yen")!=100)bad("환급/환불 금액");}
   }
   case "people"->{required(row,"kind","name","source");choice(row,"kind","JOCKEY","TRAINER");if(row.get("biography")==null)row.put("biography","");}
  }
  return row;
 }
 void person(Map<String,Object> row,String idKey,String kind,String nameKey){if(row.get(idKey)==null)return;var p=db.queryForMap("SELECT kind,name FROM person WHERE id=?",row.get(idKey));if(!kind.equals(p.get("kind")))bad("인물 구분");row.put(nameKey,p.get("name"));}
 List<Map<String,Object>> preview(Long user,String kind,List<Map<String,Object>> rows){authorize(user);if(rows==null||rows.isEmpty()||rows.size()>100)bad("한 번에 1~100행");return rows.stream().map(row->normalize(kind,row)).toList();}
 record Change(String kind,List<Map<String,Object>> rows){}
 Object saveAll(Long user,List<Change> changes){
  authorize(user);if(changes==null||changes.isEmpty()||changes.size()>10)bad("변경 묶음 1~10개");
  var affected=new TreeSet<Long>();var results=new ArrayList<Object>();
  for(var change:changes){if(change==null)bad("빈 변경 묶음");results.add(saveRows(user,change.kind(),change.rows(),affected));}
  for(long id:affected)validateRace(id);validateParents();return Map.of("batches",results);
 }
 Object save(Long user,String kind,List<Map<String,Object>> rows){return saveAll(user,List.of(new Change(kind,rows)));}
 Object saveRows(Long user,String kind,List<Map<String,Object>> rows,Set<Long> affected){
  var prepared=preview(user,kind,rows);String table=table(kind);var changed=new ArrayList<Long>();
  // Serializes catalog edits and previews against other admin writes, avoiding cross-table races.
  db.queryForList("SELECT id FROM member WHERE is_admin=TRUE ORDER BY id FOR UPDATE");
  for(var row:prepared){long id=n(row,"id");Map<String,Object> before=null;
   if(id>0){var found=db.queryForList("SELECT * FROM "+table+" WHERE id=? FOR UPDATE",id);if(found.isEmpty())throw new ApiException(404,"수정할 자료가 없습니다.");before=found.getFirst();if(n(before,"revision")!=n(row,"revision"))throw new ApiException(409,"다른 변경이 있습니다. 자료를 다시 불러오세요.");
    if(kind.equals("entries")&&(n(before,"race_id")!=n(row,"race_id")||n(before,"horse_id")!=n(row,"horse_id")))bad("기존 출전의 경주/말 변경");
    if(kind.equals("sectionals")&&n(before,"entry_id")!=n(row,"entry_id"))bad("기존 구간의 출전 변경");
    if(kind.equals("payouts")&&n(before,"race_id")!=n(row,"race_id"))bad("기존 환급표의 경주 변경");
    if(kind.equals("people")&&!str(before,"kind").equals(str(row,"kind")))bad("기존 인물의 종류 변경");
   }
   List<String> fields=List.of(FIELDS.get(kind).split(","));var values=new ArrayList<Object>();fields.forEach(f->values.add(row.get(f)));
   if(id>0){values.add(id);db.update("UPDATE "+table+" SET "+String.join(",",fields.stream().map(f->f+"=?").toList())+",revision=revision+1 WHERE id=?",values.toArray());}
   else{var key=new GeneratedKeyHolder();String sql="INSERT INTO "+table+" ("+String.join(",",fields)+") VALUES ("+String.join(",",Collections.nCopies(fields.size(),"?"))+")";db.update(c->{var ps=c.prepareStatement(sql,java.sql.Statement.RETURN_GENERATED_KEYS);for(int i=0;i<values.size();i++)ps.setObject(i+1,values.get(i));return ps;},key);id=Objects.requireNonNull(key.getKey()).longValue();}
   if(kind.equals("people")){String k=str(row,"kind");db.update(k.equals("JOCKEY")?"UPDATE entry SET jockey=?,revision=revision+1 WHERE jockey_id=?":"UPDATE horse SET trainer=?,revision=revision+1 WHERE trainer_id=?",row.get("name"),id);}
   if(kind.equals("races"))affected.add(id);
   if(Set.of("entries","payouts").contains(kind))affected.add(n(row,"race_id"));
   if(kind.equals("sectionals"))affected.add(db.queryForObject("SELECT race_id FROM entry WHERE id=?",Long.class,row.get("entry_id")));
   try{db.update("INSERT INTO catalog_audit(member_id,kind,record_id,before_json,after_json) VALUES (?,?,?,?,?)",user,kind,id,before==null?null:json.writeValueAsString(before),json.writeValueAsString(db.queryForMap("SELECT * FROM "+table+" WHERE id=?",id)));}catch(com.fasterxml.jackson.core.JsonProcessingException e){throw new IllegalStateException(e);}
   changed.add(id);
  }

  return Map.of("saved",changed.size(),"ids",changed);
 }
 void validateParents(){
  var parents=new HashMap<Long,List<Long>>();for(var h:db.queryForList("SELECT id,sire_id,dam_id FROM horse")){var p=new ArrayList<Long>();for(String k:List.of("sire_id","dam_id"))if(h.get(k)!=null)p.add(n(h,k));parents.put(n(h,"id"),p);}
  var done=new HashSet<Long>();for(long id:parents.keySet())visit(id,parents,new HashSet<>(),done);
 }
 void visit(long id,Map<Long,List<Long>> parents,Set<Long> path,Set<Long> done){if(done.contains(id))return;if(!path.add(id))bad("순환 혈통");for(long p:parents.getOrDefault(id,List.of()))visit(p,parents,path,done);path.remove(id);done.add(id);}
 void validateRace(long id){
  var race=db.queryForMap("SELECT * FROM race WHERE id=?",id);var entries=db.queryForList("SELECT * FROM entry WHERE race_id=?",id);
  long field=entries.stream().filter(e->!"SCRATCHED".equals(e.get("status"))).count();
  if("OFFICIAL".equals(race.get("status"))&&entries.stream().anyMatch(e->"DECLARED".equals(e.get("status"))))bad("결과 확정 전 미확정 출전 상태");
  if("SCHEDULED".equals(race.get("status"))&&entries.stream().anyMatch(e->!Set.of("DECLARED","SCRATCHED").contains(str(e,"status"))))bad("예정 경주의 결과");
  for(var e:entries){if(n(e,"popularity_rank")>entries.size())bad("등록 두수를 초과한 인기 순위");if(n(e,"finish_position")>field)bad("출전 두수를 초과한 착순");
   var points=db.queryForList("SELECT * FROM sectional WHERE entry_id=? ORDER BY distance",e.get("id"));
   if(!points.isEmpty()&&Set.of("DECLARED","SCRATCHED").contains(str(e,"status")))bad("미출전 말의 구간 기록");
   double previous=0;for(var p:points){if(n(p,"distance")>n(race,"distance")||n(p,"position")>field)bad("구간 거리/순위");if(p.get("cumulative_seconds")!=null){double time=decimal(p.get("cumulative_seconds")).doubleValue();if(time<=previous)bad("증가하지 않는 누적 시간");previous=time;
     if(e.get("time_seconds")!=null&&(time>decimal(e.get("time_seconds")).doubleValue()||n(p,"distance")==n(race,"distance")&&decimal(p.get("cumulative_seconds")).compareTo(decimal(e.get("time_seconds")))!=0))bad("결승 기록과 구간 기록 불일치");}
    if(n(p,"distance")==n(race,"distance")&&p.get("position")!=null&&e.get("finish_position")!=null&&n(p,"position")!=n(e,"finish_position"))bad("결승 통과 순위 불일치");
   }
  }
  for(var p:db.queryForList("SELECT * FROM payout WHERE race_id=?",id)){
   String state=str(p,"status");if(state.equals("FINAL")&&!str(race,"status").equals("OFFICIAL"))bad("결과 확정 전 확정 환급표");if(state.equals("OPEN")&&Set.of("OFFICIAL","CANCELLED").contains(str(race,"status")))bad("종료 경주의 예상 배당");
   for(String part:str(p,"combination").split("-")){long number=number(part);var e=entries.stream().filter(x->n(x,"number")==number).findFirst().orElseThrow(()->new ApiException(400,"출주표에 없는 조합 마번입니다."));if(!state.equals("REFUND")&&str(e,"status").equals("SCRATCHED"))bad("출전 취소마의 배당");}
   var selected=Arrays.stream(str(p,"combination").split("-")).map(part->entries.stream().filter(e->n(e,"number")==number(part)).findFirst().orElseThrow()).toList();
   if(state.equals("REFUND")&&!str(race,"status").equals("CANCELLED")&&selected.stream().noneMatch(e->str(e,"status").equals("SCRATCHED")))bad("환불 대상이 아닌 조합");
   if(state.equals("FINAL")){
    if(selected.stream().anyMatch(e->!str(e,"status").equals("FINISHED")||n(e,"finish_position")==0))bad("미완주 조합의 확정 환급");
    var actual=selected.stream().map(e->n(e,"finish_position")).toList();String market=str(p,"market");
    if(market.equals("PLACE")){if(actual.getFirst()>(field>=8?3:2))bad("연승 적중 착순");}
    else{
     var expected=entries.stream().filter(e->str(e,"status").equals("FINISHED")).map(e->n(e,"finish_position")).sorted().limit(selected.size()).toList();
     var positions=Set.of("QUINELLA","TRIO").contains(market)?actual.stream().sorted().toList():actual;
     if(!positions.equals(expected))bad("착순과 맞지 않는 확정 적중 조합");
    }
   }
  }
 }
 static List<Map<String,Object>> parseCsv(String csv){
  if(csv==null||csv.getBytes(java.nio.charset.StandardCharsets.UTF_8).length>200000)bad("CSV 크기(200KB 이내)");
  csv=csv.replaceFirst("^\\uFEFF","");var records=new ArrayList<List<String>>();var cells=new ArrayList<String>();var cell=new StringBuilder();boolean quoted=false,closed=false;
  for(int i=0;i<csv.length();i++){char c=csv.charAt(i);if(quoted){if(c=='"'){if(i+1<csv.length()&&csv.charAt(i+1)=='"'){cell.append('"');i++;}else{quoted=false;closed=true;}}else cell.append(c);}
   else if(c==','||c=='\n'||c=='\r'){cells.add(cell.toString());cell.setLength(0);closed=false;if(c!=','){if(c=='\r'&&i+1<csv.length()&&csv.charAt(i+1)=='\n')i++;records.add(List.copyOf(cells));cells.clear();}}
   else if(c=='"'&&cell.isEmpty()&&!closed)quoted=true;else{if(closed||c=='"')bad("CSV 따옴표");cell.append(c);}}
  if(quoted)bad("CSV 닫히지 않은 따옴표");if(!cell.isEmpty()||!cells.isEmpty()||closed){cells.add(cell.toString());records.add(cells);}
  if(records.size()<2||records.size()>101)bad("CSV 1~100행");var header=records.getFirst();if(new HashSet<>(header).size()!=header.size())bad("CSV 중복 열");var rows=new ArrayList<Map<String,Object>>();
  for(var values:records.subList(1,records.size())){if(values.size()!=header.size())bad("CSV 열 수");var row=new LinkedHashMap<String,Object>();for(int i=0;i<header.size();i++)row.put(header.get(i),values.get(i));rows.add(row);}return rows;
 }
}
@RestController @RequestMapping("/api/admin")
class CatalogAdminController {
 final CatalogAdmin service;CatalogAdminController(CatalogAdmin service){this.service=service;}
 @PostMapping("/changes") Object changes(@AuthenticationPrincipal Long user,@RequestBody List<CatalogAdmin.Change> changes){return service.saveAll(user,changes);}
 @DeleteMapping("/{kind}/{id}") @ResponseStatus(org.springframework.http.HttpStatus.NO_CONTENT) void remove(@AuthenticationPrincipal Long user,@PathVariable String kind,@PathVariable long id,@RequestParam long revision){service.remove(user,kind,id,revision);}
 @GetMapping("/access") Object access(@AuthenticationPrincipal Long user){service.authorize(user);return Map.of("admin",true);}
 @GetMapping("/audit") Object audit(@AuthenticationPrincipal Long user){return service.audit(user);}
 @GetMapping("/{kind}") Object list(@AuthenticationPrincipal Long user,@PathVariable String kind,@RequestParam(defaultValue="0") int page){return service.list(user,kind,page);}
 @PostMapping("/{kind}/preview") Object preview(@AuthenticationPrincipal Long user,@PathVariable String kind,@RequestBody CatalogAdmin.Batch input){return service.preview(user,kind,input.rows());}
 @PostMapping("/{kind}/save") Object save(@AuthenticationPrincipal Long user,@PathVariable String kind,@RequestBody CatalogAdmin.Batch input){return service.save(user,kind,input.rows());}
 @PostMapping("/{kind}/csv-preview") Object csv(@AuthenticationPrincipal Long user,@PathVariable String kind,@RequestBody CatalogAdmin.Csv input){service.authorize(user);return service.preview(user,kind,CatalogAdmin.parseCsv(input.csv()));}
}
