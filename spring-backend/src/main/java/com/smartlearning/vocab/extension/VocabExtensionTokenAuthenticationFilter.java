package com.smartlearning.vocab.extension;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.HttpMethod;
import org.springframework.security.authentication.AbstractAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

public class VocabExtensionTokenAuthenticationFilter extends OncePerRequestFilter {

    public static final String EXTENSION_TOKEN_HEADER = "X-SLSS-Extension-Token";

    private final VocabExtensionAuthService authService;

    public VocabExtensionTokenAuthenticationFilter(VocabExtensionAuthService authService) {
        this.authService = authService;
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {
        String token = request.getHeader(EXTENSION_TOKEN_HEADER);
        if (token == null || token.isBlank()) {
            filterChain.doFilter(request, response);
            return;
        }

        if (!isExtensionVocabularyRequest(request)) {
            response.sendError(HttpServletResponse.SC_UNAUTHORIZED, "Extension token is not accepted for this endpoint");
            return;
        }

        UUID userId = authService.resolveUserId(token).orElse(null);
        if (userId == null) {
            response.sendError(HttpServletResponse.SC_UNAUTHORIZED, "Invalid extension token");
            return;
        }

        SecurityContextHolder.getContext().setAuthentication(buildAuthentication(userId));
        filterChain.doFilter(request, response);
    }

    private static boolean isExtensionVocabularyRequest(HttpServletRequest request) {
        if (!HttpMethod.POST.matches(request.getMethod())) {
            return false;
        }
        String path = request.getRequestURI();
        return "/api/v1/vocab/lookup".equals(path) || "/api/v1/vocab/capture".equals(path);
    }

    private static AbstractAuthenticationToken buildAuthentication(UUID userId) {
        Instant now = Instant.now();
        Jwt jwt = Jwt.withTokenValue("extension-session")
                .header("alg", "none")
                .subject(userId.toString())
                .issuedAt(now)
                .expiresAt(now.plusSeconds(60))
                .claim("token_use", "firefox_extension")
                .build();

        return new JwtAuthenticationToken(
                jwt,
                List.of(new SimpleGrantedAuthority("SCOPE_vocab:extension"))
        );
    }
}
