package com.smartlearning.vocab;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Size;
import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.NotBlank;

public record VocabCaptureRequest(
        @NotBlank
        @Length(max = 255)
        String term,

        String meaning,

        @JsonProperty("translation_vi")
        String translationVi,

        @JsonProperty("definition_en")
        String definitionEn,

        @JsonProperty("example_sentence")
        @Size(max = 1000)
        String exampleSentence,

        @JsonProperty("part_of_speech")
        @Size(max = 80)
        String partOfSpeech,

        @Size(max = 255)
        String phonetic,

        @JsonProperty("audio_url")
        @Size(max = 2000)
        String audioUrl,

        @JsonProperty("dictionary_provider")
        @Size(max = 100)
        String dictionaryProvider,

        @JsonProperty("translation_provider")
        @Size(max = 100)
        String translationProvider,

        @JsonProperty("context_sentence")
        @Size(max = 1000)
        String contextSentence,

        @JsonProperty("page_url")
        @Size(max = 2000)
        String pageUrl,

        @JsonProperty("page_title")
        @Size(max = 255)
        String pageTitle
) {
}
