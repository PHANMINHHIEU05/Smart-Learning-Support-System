package com.smartlearning.vocab.extension;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.security.SecureRandom;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.Base64;
import java.util.Locale;
import java.util.Optional;
import java.util.UUID;

@Service
public class VocabExtensionAuthService {

    private static final char[] PAIRING_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789".toCharArray();
    private static final int PAIRING_CODE_LENGTH = 8;
    private static final int RAW_TOKEN_BYTES = 32;
    private static final int MAX_GENERATION_ATTEMPTS = 8;

    private final VocabExtensionPairingCodeRepository pairingCodeRepository;
    private final VocabExtensionSessionRepository sessionRepository;
    private final VocabExtensionTokenHasher tokenHasher;
    private final SecureRandom secureRandom = new SecureRandom();
    private final Duration pairingCodeTtl;
    private final Duration sessionTtl;

    public VocabExtensionAuthService(
            VocabExtensionPairingCodeRepository pairingCodeRepository,
            VocabExtensionSessionRepository sessionRepository,
            VocabExtensionTokenHasher tokenHasher,
            @Value("${app.vocabulary.extension.pairing-code-ttl-minutes:10}") long pairingCodeTtlMinutes,
            @Value("${app.vocabulary.extension.session-ttl-days:90}") long sessionTtlDays
    ) {
        this.pairingCodeRepository = pairingCodeRepository;
        this.sessionRepository = sessionRepository;
        this.tokenHasher = tokenHasher;
        this.pairingCodeTtl = Duration.ofMinutes(pairingCodeTtlMinutes);
        this.sessionTtl = Duration.ofDays(sessionTtlDays);
    }

    @Transactional
    public CreatePairingCodeResponse createPairingCode(UUID userId) {
        OffsetDateTime now = OffsetDateTime.now();
        String code = generateUniquePairingCode();
        VocabExtensionPairingCode pairingCode = new VocabExtensionPairingCode();
        pairingCode.setUserId(userId);
        pairingCode.setCodeHash(tokenHasher.sha256Hex(normalizePairingCode(code)));
        pairingCode.setExpiresAt(now.plus(pairingCodeTtl));
        pairingCodeRepository.save(pairingCode);

        return new CreatePairingCodeResponse(code, pairingCode.getExpiresAt(), pairingCodeTtl.toSeconds());
    }

    @Transactional
    public ExchangePairingCodeResponse exchangePairingCode(ExchangePairingCodeRequest request) {
        OffsetDateTime now = OffsetDateTime.now();
        String codeHash = tokenHasher.sha256Hex(normalizePairingCode(request.pairingCode()));
        VocabExtensionPairingCode pairingCode = pairingCodeRepository.findByCodeHash(codeHash)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid pairing code"));

        if (pairingCode.getConsumedAt() != null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Pairing code already used");
        }
        if (!pairingCode.getExpiresAt().isAfter(now)) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Pairing code expired");
        }

        String rawToken = generateUniqueSessionToken();
        VocabExtensionSession session = new VocabExtensionSession();
        session.setUserId(pairingCode.getUserId());
        session.setTokenHash(tokenHasher.sha256Hex(rawToken));
        session.setDeviceLabel(blankToNull(request.deviceLabel()));
        session.setExpiresAt(now.plus(sessionTtl));
        sessionRepository.save(session);

        pairingCode.setConsumedAt(now);
        pairingCodeRepository.save(pairingCode);

        return new ExchangePairingCodeResponse(rawToken, session.getExpiresAt(), "Extension");
    }

    @Transactional
    public Optional<UUID> resolveUserId(String rawToken) {
        if (rawToken == null || rawToken.isBlank()) {
            return Optional.empty();
        }

        OffsetDateTime now = OffsetDateTime.now();
        return sessionRepository.findByTokenHashAndRevokedAtIsNull(tokenHasher.sha256Hex(rawToken.trim()))
                .filter(session -> session.getExpiresAt().isAfter(now))
                .map(session -> {
                    session.setLastUsedAt(now);
                    sessionRepository.save(session);
                    return session.getUserId();
                });
    }

    private String generateUniquePairingCode() {
        for (int attempt = 0; attempt < MAX_GENERATION_ATTEMPTS; attempt++) {
            String code = generatePairingCode();
            if (!pairingCodeRepository.existsByCodeHash(tokenHasher.sha256Hex(normalizePairingCode(code)))) {
                return code;
            }
        }
        throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "Could not generate pairing code");
    }

    private String generatePairingCode() {
        StringBuilder builder = new StringBuilder(PAIRING_CODE_LENGTH + 1);
        for (int index = 0; index < PAIRING_CODE_LENGTH; index++) {
            if (index == 4) {
                builder.append('-');
            }
            builder.append(PAIRING_ALPHABET[secureRandom.nextInt(PAIRING_ALPHABET.length)]);
        }
        return builder.toString();
    }

    private String generateUniqueSessionToken() {
        for (int attempt = 0; attempt < MAX_GENERATION_ATTEMPTS; attempt++) {
            byte[] bytes = new byte[RAW_TOKEN_BYTES];
            secureRandom.nextBytes(bytes);
            String token = Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
            if (!sessionRepository.existsByTokenHash(tokenHasher.sha256Hex(token))) {
                return token;
            }
        }
        throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "Could not generate extension token");
    }

    private static String normalizePairingCode(String code) {
        return code == null
                ? ""
                : code.replace("-", "").replace(" ", "").trim().toUpperCase(Locale.ROOT);
    }

    private static String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }
}
