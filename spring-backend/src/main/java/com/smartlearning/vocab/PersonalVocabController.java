package com.smartlearning.vocab;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

@Validated
@RestController
@RequestMapping("/api/v1/vocab/personal")
public class PersonalVocabController {

    private final VocabService service;
    private final PersonalVocabProperties properties;

    public PersonalVocabController(VocabService service, PersonalVocabProperties properties) {
        this.service = service;
        this.properties = properties;
    }

    @PostMapping("/capture")
    public VocabEntryResponse capture(@Valid @RequestBody VocabCaptureRequest request) {
        return service.capturePersonal(properties.userId(), request);
    }

    @GetMapping({"", "/"})
    public List<VocabEntryResponse> list(
            @RequestParam(required = false) VocabStatus status,
            @RequestParam(defaultValue = "0") @Min(0) int offset,
            @RequestParam(defaultValue = "50") @Min(1) @Max(200) int limit
    ) {
        return service.list(properties.userId(), status, offset, limit);
    }

    @GetMapping("/due")
    public List<VocabEntryResponse> due(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) OffsetDateTime now,
            @RequestParam(defaultValue = "50") @Min(1) @Max(200) int limit
    ) {
        return service.dueLearning(properties.userId(), now, limit);
    }

    @PostMapping("/{vocabId}/review")
    public VocabEntryResponse review(
            @PathVariable UUID vocabId,
            @Valid @RequestBody ReviewVocabRequest request
    ) {
        return service.review(properties.userId(), vocabId, request);
    }

    @PostMapping("/{vocabId}/quiz-result")
    public VocabEntryResponse quizResult(
            @PathVariable UUID vocabId,
            @Valid @RequestBody QuizResultRequest request
    ) {
        return service.applyQuizResult(properties.userId(), vocabId, request);
    }
}
