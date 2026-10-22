package dev.keiba;
import java.util.Map;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
@RestControllerAdvice
class ApiExceptionHandler {
 @ExceptionHandler(ApiException.class) ResponseEntity<?> domain(ApiException e) { return ResponseEntity.status(e.status).body(Map.of("message",e.getMessage())); }
 @ExceptionHandler({MethodArgumentNotValidException.class, MethodArgumentTypeMismatchException.class, org.springframework.http.converter.HttpMessageNotReadableException.class, jakarta.validation.ConstraintViolationException.class, org.springframework.web.method.annotation.HandlerMethodValidationException.class})
 ResponseEntity<?> invalid(Exception e) { return ResponseEntity.badRequest().body(Map.of("message","입력값을 확인하세요. 날짜, 이메일, 비밀번호 길이 등 형식이 올바르지 않습니다.")); }
 @ExceptionHandler(DataIntegrityViolationException.class) ResponseEntity<?> duplicate(Exception e) { return ResponseEntity.status(409).body(Map.of("message","이미 등록된 항목입니다.")); }
}
