FROM eclipse-temurin:21-jdk-jammy

# Install git and other necessary tools
RUN apt-get update && \
    apt-get install -y git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

CMD ["bash"]