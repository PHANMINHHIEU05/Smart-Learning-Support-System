package com.smartlearning.security;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtDecoders;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.util.StringUtils;

import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;

@Configuration
public class JwtDecoderConfig {

    @Bean
    @ConditionalOnProperty(name = "app.security.jwt.enabled", havingValue = "true", matchIfMissing = true)
    JwtDecoder jwtDecoder(
            @Value("${app.security.jwt.issuer-uri:}") String issuerUri,
            @Value("${app.security.jwt.jwk-set-uri:}") String jwkSetUri,
            @Value("${app.security.jwt.secret:}") String jwtSecret,
            @Value("${app.security.jwt.supabase-url:}") String supabaseUrl,
            @Value("${app.security.jwt.supabase-anon-key:}") String supabaseAnonKey,
            @Value("${app.security.jwt.remote-fallback-enabled:true}") boolean remoteFallbackEnabled
    ) {
        JwtDecoder localDecoder = null;

        if (StringUtils.hasText(jwkSetUri)) {
            localDecoder = NimbusJwtDecoder.withJwkSetUri(jwkSetUri).build();
        } else if (StringUtils.hasText(issuerUri)) {
            localDecoder = JwtDecoders.fromIssuerLocation(issuerUri);
        } else if (StringUtils.hasText(jwtSecret)) {
            SecretKeySpec secretKey = new SecretKeySpec(
                    jwtSecret.getBytes(StandardCharsets.UTF_8),
                    "HmacSHA256"
            );

            localDecoder = NimbusJwtDecoder
                    .withSecretKey(secretKey)
                    .macAlgorithm(MacAlgorithm.HS256)
                    .build();
        }

        if (
                remoteFallbackEnabled
                        && StringUtils.hasText(supabaseUrl)
                        && StringUtils.hasText(supabaseAnonKey)
        ) {
            return new SupabaseFallbackJwtDecoder(localDecoder, supabaseUrl, supabaseAnonKey);
        }

        if (localDecoder != null) {
            return localDecoder;
        }

        throw new IllegalStateException(
                "JWT auth is enabled. Set APP_SECURITY_JWT_ISSUER_URI, APP_SECURITY_JWT_JWK_SET_URI, APP_SECURITY_JWT_SECRET, or SUPABASE_URL + SUPABASE_ANON_KEY."
        );
    }
}
