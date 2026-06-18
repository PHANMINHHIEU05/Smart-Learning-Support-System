package com.smartlearning.vocab;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.web.client.RestClient;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;

class VocabEnrichmentClientTest {

    private HttpServer server;
    private String baseUrl;

    @BeforeEach
    void setUp() throws IOException {
        server = HttpServer.create(new InetSocketAddress(0), 0);
        server.start();
        baseUrl = "http://localhost:" + server.getAddress().getPort();
    }

    @AfterEach
    void tearDown() {
        if (server != null) {
            server.stop(0);
        }
    }

    @Test
    void sendsInternalTokenAndParsesEnrichedVocabulary() {
        AtomicReference<String> observedToken = new AtomicReference<>();
        AtomicReference<String> observedBody = new AtomicReference<>();

        server.createContext("/internal/v1/vocabulary/lookup", exchange -> {
            observedToken.set(exchange.getRequestHeaders().getFirst("X-Internal-Token"));
            observedBody.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            respond(exchange, 200, """
                    {
                      "term": "consequence",
                      "normalized_term": "consequence",
                      "meaning": "hậu quả",
                      "translation_vi": "hậu quả",
                      "definition_en": "a result of an action",
                      "example_sentence": "Every action has a consequence.",
                      "part_of_speech": "noun",
                      "phonetic": "/test/",
                      "audio_url": "https://audio.test/consequence.mp3",
                      "dictionary_provider": "dictionaryapi.dev",
                      "translation_provider": "mymemory"
                    }
                    """);
        });

        VocabEnrichmentClient client = new VocabEnrichmentClient(
                RestClient.builder().build(),
                baseUrl,
                "shared-token",
                true
        );

        Optional<VocabEnrichmentResponse> result = client.lookup(
                "consequence",
                "Every action has a consequence."
        );

        assertThat(result).isPresent();
        assertThat(result.orElseThrow().translationVi()).isEqualTo("hậu quả");
        assertThat(result.orElseThrow().partOfSpeech()).isEqualTo("noun");
        assertThat(observedToken.get()).isEqualTo("shared-token");
        assertThat(observedBody.get()).contains("\"term\":\"consequence\"");
        assertThat(observedBody.get()).contains("\"context_sentence\":\"Every action has a consequence.\"");
    }

    @Test
    void returnsEmptyWhenWorkerFails() {
        server.createContext("/internal/v1/vocabulary/lookup", exchange ->
                respond(exchange, 503, "{\"detail\":\"provider unavailable\"}")
        );

        VocabEnrichmentClient client = new VocabEnrichmentClient(
                RestClient.builder().build(),
                baseUrl,
                "shared-token",
                true
        );

        assertThat(client.lookup("resilient", null)).isEmpty();
    }

    private static void respond(HttpExchange exchange, int status, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().add(HttpHeaders.CONTENT_TYPE, "application/json");
        exchange.sendResponseHeaders(status, bytes.length);
        exchange.getResponseBody().write(bytes);
        exchange.close();
    }
}
