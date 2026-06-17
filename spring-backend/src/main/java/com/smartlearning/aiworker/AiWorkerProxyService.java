package com.smartlearning.aiworker;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.util.UriComponentsBuilder;

import java.net.URI;
import java.util.Collections;
import java.util.List;
import java.util.Locale;

@Service
public class AiWorkerProxyService {

    private static final List<String> HOP_BY_HOP_HEADERS = List.of(
            "connection",
            "keep-alive",
            "proxy-authenticate",
            "proxy-authorization",
            "te",
            "trailer",
            "transfer-encoding",
            "upgrade",
            "host",
            "content-length"
    );

    private final RestClient restClient;
    private final String aiWorkerBaseUrl;

    public AiWorkerProxyService(
            RestClient aiWorkerRestClient,
            @Value("${app.ai-worker.base-url:http://localhost:8001}") String aiWorkerBaseUrl
    ) {
        this.restClient = aiWorkerRestClient;
        this.aiWorkerBaseUrl = removeTrailingSlash(aiWorkerBaseUrl);
    }

    public ResponseEntity<byte[]> forward(HttpServletRequest request, byte[] body) {
        URI targetUri = buildTargetUri(request);
        HttpMethod method = HttpMethod.valueOf(request.getMethod());

        try {
            return restClient.method(method)
                    .uri(targetUri)
                    .headers(headers -> copyRequestHeaders(request, headers))
                    .body(body == null ? new byte[0] : body)
                    .exchange((clientRequest, clientResponse) -> {
                        byte[] responseBody = clientResponse.getBody() == null
                                ? new byte[0]
                                : clientResponse.getBody().readAllBytes();
                        HttpHeaders responseHeaders = new HttpHeaders();
                        clientResponse.getHeaders().forEach((name, values) -> {
                            if (!isHopByHop(name)) {
                                responseHeaders.addAll(name, values);
                            }
                        });
                        return ResponseEntity
                                .status(clientResponse.getStatusCode())
                                .headers(responseHeaders)
                                .body(responseBody);
                    });
        } catch (ResourceAccessException ex) {
            return ResponseEntity
                    .status(HttpStatus.BAD_GATEWAY)
                    .header(HttpHeaders.CONTENT_TYPE, "application/json")
                    .body(("{\"message\":\"AI worker unavailable\",\"detail\":\""
                            + sanitize(ex.getMessage()) + "\"}").getBytes());
        } catch (RuntimeException ex) {
            return ResponseEntity
                    .status(HttpStatus.BAD_GATEWAY)
                    .header(HttpHeaders.CONTENT_TYPE, "application/json")
                    .body(("{\"message\":\"AI worker proxy failed\",\"detail\":\""
                            + sanitize(ex.getMessage()) + "\"}").getBytes());
        }
    }

    private URI buildTargetUri(HttpServletRequest request) {
        String queryString = request.getQueryString();
        UriComponentsBuilder builder = UriComponentsBuilder
                .fromHttpUrl(aiWorkerBaseUrl)
                .path(request.getRequestURI());

        if (queryString != null && !queryString.isBlank()) {
            builder.query(queryString);
        }

        return builder.build(true).toUri();
    }

    private static void copyRequestHeaders(HttpServletRequest request, HttpHeaders targetHeaders) {
        Collections.list(request.getHeaderNames()).forEach(name -> {
            if (isHopByHop(name)) {
                return;
            }
            Collections.list(request.getHeaders(name))
                    .forEach(value -> targetHeaders.add(name, value));
        });
    }

    private static boolean isHopByHop(String headerName) {
        return HOP_BY_HOP_HEADERS.contains(headerName.toLowerCase(Locale.ROOT));
    }

    private static String removeTrailingSlash(String value) {
        if (value == null || value.isBlank()) {
            return "http://localhost:8001";
        }
        return value.endsWith("/") ? value.substring(0, value.length() - 1) : value;
    }

    private static String sanitize(String value) {
        if (value == null) {
            return "";
        }
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
    }
}
