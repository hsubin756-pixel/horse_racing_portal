package dev.keiba.common;

/** 서비스 계층에서 던지는 HTTP 상태 코드가 있는 예외. ApiExceptionHandler가 {"message": ...} 응답으로 바꿉니다. */
public class ApiException extends RuntimeException {

    private final int status;

    public ApiException(int status, String message) {
        super(message);
        this.status = status;
    }

    public int status() {
        return status;
    }
}
