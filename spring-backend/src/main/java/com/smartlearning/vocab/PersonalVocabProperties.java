package com.smartlearning.vocab;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.UUID;

@ConfigurationProperties(prefix = "app.vocabulary.personal")
public record PersonalVocabProperties(
        UUID userId
) {
    public PersonalVocabProperties {
        if (userId == null) {
            userId = UUID.fromString("00000000-0000-0000-0000-000000000001");
        }
    }
}
