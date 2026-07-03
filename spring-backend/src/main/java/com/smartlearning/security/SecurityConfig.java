package com.smartlearning.security;

import com.smartlearning.vocab.extension.VocabExtensionTokenAuthenticationFilter;
import com.smartlearning.vocab.extension.VocabExtensionAuthService;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.oauth2.server.resource.web.authentication.BearerTokenAuthenticationFilter;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    private final boolean jwtEnabled;
    private final ObjectProvider<VocabExtensionAuthService> extensionAuthServiceProvider;

    public SecurityConfig(
            @Value("${app.security.jwt.enabled:true}") boolean jwtEnabled,
            ObjectProvider<VocabExtensionAuthService> extensionAuthServiceProvider
    ) {
        this.jwtEnabled = jwtEnabled;
        this.extensionAuthServiceProvider = extensionAuthServiceProvider;
    }

    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
                .csrf(AbstractHttpConfigurer::disable)
                .cors(Customizer.withDefaults())
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers("/api/v1/health", "/actuator/health", "/actuator/info").permitAll()
                        .requestMatchers(HttpMethod.POST, "/api/v1/logs").permitAll()
                        .requestMatchers(HttpMethod.POST, "/api/v1/vocab/extension/exchange").permitAll()
                        .requestMatchers("/api/v1/vocab/personal/**").permitAll()
                        .anyRequest().authenticated()
                )
                .httpBasic(AbstractHttpConfigurer::disable)
                .formLogin(AbstractHttpConfigurer::disable);

        VocabExtensionAuthService extensionAuthService = extensionAuthServiceProvider.getIfAvailable();
        if (extensionAuthService != null) {
            http.addFilterBefore(
                    new VocabExtensionTokenAuthenticationFilter(extensionAuthService),
                    BearerTokenAuthenticationFilter.class
            );
        }

        if (jwtEnabled) {
            http.oauth2ResourceServer(oauth2 -> oauth2.jwt(Customizer.withDefaults()));
        }

        return http.build();
    }
}
