package com.smartlearning.vocab;

import com.fasterxml.jackson.annotation.JsonProperty;

public record VocabEnrichmentRequest(
        String term,

        @JsonProperty("context_sentence")
        String contextSentence
) {
}
