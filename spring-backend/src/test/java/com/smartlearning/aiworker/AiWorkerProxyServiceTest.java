package com.smartlearning.aiworker;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.web.client.RestClient;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;

class AiWorkerProxyServiceTest {

    private HttpServer server;
    private String baseUrl;
    private AiWorkerProxyService service;

    @BeforeEach
    void setUp() throws IOException {
        server = HttpServer.create(new InetSocketAddress(0), 0);
        server.start();
        baseUrl = "http://localhost:" + server.getAddress().getPort();
        service = new AiWorkerProxyService(RestClient.builder().build(), baseUrl);
    }

    @AfterEach
    void tearDown() {
        if (server != null) {
            server.stop(0);
        }
    }

    @Test
    void forwardsMethodQueryHeadersAndBody() {
        AtomicReference<String> observedMethod = new AtomicReference<>();
        AtomicReference<String> observedQuery = new AtomicReference<>();
        AtomicReference<String> observedAuthorization = new AtomicReference<>();
        AtomicReference<String> observedContentType = new AtomicReference<>();
        AtomicReference<String> observedBody = new AtomicReference<>();

        server.createContext("/api/v1/ai-events/batch", exchange -> {
            observedMethod.set(exchange.getRequestMethod());
            observedQuery.set(exchange.getRequestURI().getQuery());
            observedAuthorization.set(exchange.getRequestHeaders().getFirst(HttpHeaders.AUTHORIZATION));
            observedContentType.set(exchange.getRequestHeaders().getFirst(HttpHeaders.CONTENT_TYPE));
            observedBody.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            respond(exchange, 201, "{\"ok\":true}");
        });

        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/api/v1/ai-events/batch");
        request.setQueryString("session_id=abc&limit=20");
        request.addHeader(HttpHeaders.AUTHORIZATION, "Bearer test-token");
        request.addHeader(HttpHeaders.CONTENT_TYPE, "application/json");
        request.addHeader(HttpHeaders.ACCEPT, "application/json");

        ResponseEntity<byte[]> response = service.forward(
                request,
                "{\"events\":[]}".getBytes(StandardCharsets.UTF_8)
        );

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        assertThat(new String(response.getBody(), StandardCharsets.UTF_8)).isEqualTo("{\"ok\":true}");
        assertThat(observedMethod.get()).isEqualTo("POST");
        assertThat(observedQuery.get()).isEqualTo("session_id=abc&limit=20");
        assertThat(observedAuthorization.get()).isEqualTo("Bearer test-token");
        assertThat(observedContentType.get()).startsWith("application/json");
        assertThat(observedBody.get()).isEqualTo("{\"events\":[]}");
    }

    @Test
    void propagatesWorkerErrorStatusAndBody() {
        server.createContext("/api/v1/monitoring/start", exchange ->
                respond(exchange, 503, "{\"detail\":\"camera unavailable\"}")
        );

        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/api/v1/monitoring/start");
        request.addHeader(HttpHeaders.CONTENT_TYPE, "application/json");

        ResponseEntity<byte[]> response = service.forward(
                request,
                "{\"session_id\":\"abc\"}".getBytes(StandardCharsets.UTF_8)
        );

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.SERVICE_UNAVAILABLE);
        assertThat(new String(response.getBody(), StandardCharsets.UTF_8))
                .isEqualTo("{\"detail\":\"camera unavailable\"}");
    }

    private static void respond(HttpExchange exchange, int status, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().add(HttpHeaders.CONTENT_TYPE, "application/json");
        exchange.sendResponseHeaders(status, bytes.length);
        exchange.getResponseBody().write(bytes);
        exchange.close();
    }
}
