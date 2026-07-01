package com.smartlearning.security;

import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.SignedJWT;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpHeaders;
import org.springframework.security.oauth2.jwt.BadJwtException;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtException;
import org.springframework.util.StringUtils;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

import java.text.ParseException;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

final class SupabaseFallbackJwtDecoder implements JwtDecoder {

    private static final ParameterizedTypeReference<Map<String, Object>> USER_RESPONSE_TYPE =
            new ParameterizedTypeReference<>() {
            };

    private final JwtDecoder delegate;
    private final RestClient restClient;
    private final String userInfoUri;
    private final String anonKey;
    private final ConcurrentMap<String, Jwt> remoteCache = new ConcurrentHashMap<>();

    SupabaseFallbackJwtDecoder(
            JwtDecoder delegate,
            String supabaseUrl,
            String anonKey
    ) {
        this.delegate = delegate;
        this.anonKey = anonKey;
        this.userInfoUri = normalizeBaseUrl(supabaseUrl) + "/auth/v1/user";
        this.restClient = RestClient.create();
    }

    @Override
    public Jwt decode(String token) throws JwtException {
        if (delegate != null) {
            try {
                return delegate.decode(token);
            } catch (JwtException ignored) {
                // Fall back to Supabase Auth for projects whose tokens cannot be verified locally.
            }
        }

        Jwt cached = remoteCache.get(token);
        if (cached != null && cached.getExpiresAt() != null && cached.getExpiresAt().isAfter(Instant.now().plusSeconds(5))) {
            return cached;
        }

        Jwt jwt = decodeWithSupabase(token);
        remoteCache.put(token, jwt);
        return jwt;
    }

    private Jwt decodeWithSupabase(String token) {
        Map<String, Object> user;
        try {
            user = restClient.get()
                    .uri(userInfoUri)
                    .header("apikey", anonKey)
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
                    .retrieve()
                    .body(USER_RESPONSE_TYPE);
        } catch (RestClientResponseException ex) {
            throw new BadJwtException("Supabase rejected the access token", ex);
        } catch (RestClientException ex) {
            throw new BadJwtException("Could not verify access token with Supabase", ex);
        }

        if (user == null || !StringUtils.hasText(asString(user.get("id")))) {
            throw new BadJwtException("Supabase user response did not include an id");
        }

        try {
            SignedJWT parsed = SignedJWT.parse(token);
            JWTClaimsSet claimSet = parsed.getJWTClaimsSet();
            Map<String, Object> claims = new LinkedHashMap<>(claimSet.getClaims());
            Map<String, Object> headers = new LinkedHashMap<>(parsed.getHeader().toJSONObject());

            claims.putIfAbsent("sub", asString(user.get("id")));
            claims.putIfAbsent("email", asString(user.get("email")));
            claims.putIfAbsent("role", asString(user.get("role")));

            Instant issuedAt = toInstant(claimSet.getIssueTime());
            Instant expiresAt = toInstant(claimSet.getExpirationTime());
            if (expiresAt == null) {
                expiresAt = Instant.now().plusSeconds(60);
            }

            return new Jwt(token, issuedAt, expiresAt, headers, claims);
        } catch (ParseException ex) {
            throw new BadJwtException("Supabase token could not be parsed after verification", ex);
        }
    }

    private static String normalizeBaseUrl(String value) {
        String trimmed = value.trim();
        return trimmed.endsWith("/") ? trimmed.substring(0, trimmed.length() - 1) : trimmed;
    }

    private static Instant toInstant(java.util.Date date) {
        return date == null ? null : date.toInstant();
    }

    private static String asString(Object value) {
        return value == null ? null : value.toString();
    }
}
