# Build and test with scripts/build.sh before assembling this runtime image.
FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --chown=10001:10001 build/libs/keiba-portal-0.1.0.jar app.jar
USER 10001
EXPOSE 8080
ENTRYPOINT ["java","-XX:MaxRAMPercentage=70","-jar","app.jar"]
