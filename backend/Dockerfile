FROM gradle:8.14.3-jdk21 AS build
WORKDIR /app
COPY --chown=gradle:gradle . .
USER gradle
RUN gradle --no-daemon --max-workers=2 bootJar
FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /app/build/libs/keiba-portal-0.1.0.jar app.jar
USER 10001
EXPOSE 8080
ENTRYPOINT ["java","-XX:MaxRAMPercentage=70","-jar","app.jar"]
