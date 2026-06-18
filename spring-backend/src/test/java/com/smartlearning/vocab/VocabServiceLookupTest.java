package com.smartlearning.vocab;

import org.junit.jupiter.api.Test;

import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class VocabServiceLookupTest {

    @Test
    void combinesWorkerEnrichmentWithUserSavedState() {
        UUID userId = UUID.randomUUID();
        VocabEntryRepository repository = mock(VocabEntryRepository.class);
        VocabLookupCacheService cacheService = mock(VocabLookupCacheService.class);
        when(repository.existsByUserIdAndTermIgnoreCase(userId, "Consequence")).thenReturn(true);
        when(cacheService.resolve("Consequence"))
                .thenReturn(Optional.of(new VocabEnrichmentResponse(
                        "Consequence",
                        "consequence",
                        "hậu quả",
                        "hậu quả",
                        "a result of an action",
                        "Every action has a consequence.",
                        "noun",
                        "/test/",
                        "https://audio.test/consequence.mp3",
                        "dictionaryapi.dev",
                        "mymemory"
                )));

        VocabService service = new VocabService(repository, cacheService);
        VocabLookupResponse response = service.lookup(
                userId,
                new VocabLookupRequest(
                        "Consequence",
                        "Every action has a consequence.",
                        "https://example.com/article",
                        "Example"
                )
        );

        assertThat(response.normalizedTerm()).isEqualTo("consequence");
        assertThat(response.meaning()).isEqualTo("hậu quả");
        assertThat(response.translationVi()).isEqualTo("hậu quả");
        assertThat(response.definitionEn()).isEqualTo("a result of an action");
        assertThat(response.partOfSpeech()).isEqualTo("noun");
        assertThat(response.alreadySaved()).isTrue();
    }
}
