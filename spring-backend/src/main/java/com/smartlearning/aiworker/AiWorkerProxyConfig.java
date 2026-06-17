package com.smartlearning.aiworker;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestClient;

@Configuration
public class AiWorkerProxyConfig {

    @Bean
    RestClient aiWorkerRestClient(RestClient.Builder builder) {
        return builder.build();
    }
}
