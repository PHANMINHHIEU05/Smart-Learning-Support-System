package com.smartlearning.vocab;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import java.util.Optional;

@Component
public class VocabEnrichmentClient {

    private static final Logger LOGGER = LoggerFactory.getLogger(VocabEnrichmentClient.class);

    private final RestClient restClient;
    private final String lookupUrl;
    private final String internalToken;
    private final boolean enabled;

    public VocabEnrichmentClient(
            RestClient aiWorkerRestClient,
            @Value("${app.ai-worker.base-url:http://localhost:8001}") String aiWorkerBaseUrl,
            @Value("${app.ai-worker.internal-token:dev-internal-token}") String internalToken,
            @Value("${app.ai-worker.vocabulary-enabled:true}") boolean enabled
    ) {
        this.restClient = aiWorkerRestClient;
        this.lookupUrl = removeTrailingSlash(aiWorkerBaseUrl) + "/internal/v1/vocabulary/lookup";
        this.internalToken = internalToken;
        this.enabled = enabled;
    }

    public Optional<VocabEnrichmentResponse> lookup(String term, String contextSentence) {
        if (!enabled) {
            return Optional.empty();
        }

        try {
            return Optional.ofNullable(restClient.post()
                    .uri(lookupUrl)
                    .header("X-Internal-Token", internalToken)
                    .header(HttpHeaders.CONTENT_TYPE, "application/json")
                    .body(new VocabEnrichmentRequest(term, contextSentence))
                    .retrieve()
                    .body(VocabEnrichmentResponse.class));
        } catch (RestClientException ex) {
            LOGGER.warn("Vocabulary enrichment worker unavailable: {}", ex.getClass().getSimpleName());
            return Optional.empty();
        }
    }

    private static String removeTrailingSlash(String value) {
        if (value == null || value.isBlank()) {
            return "http://localhost:8001";
        }
        return value.endsWith("/") ? value.substring(0, value.length() - 1) : value;
    }
}
