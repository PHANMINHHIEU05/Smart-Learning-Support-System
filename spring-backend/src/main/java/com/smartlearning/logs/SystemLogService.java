package com.smartlearning.logs;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class SystemLogService {

    private final SystemLogRepository repository;

    public SystemLogService(SystemLogRepository repository) {
        this.repository = repository;
    }

    @Transactional
    public SystemLogResponse create(CreateSystemLogRequest request) {
        SystemLog log = new SystemLog();
        log.setSourceService(request.sourceService());
        log.setSeverity(request.severity());
        log.setCategory(request.category());
        log.setMessage(request.message());
        log.setCorrelationId(request.correlationId());
        log.setPayloadJson(request.safePayload());

        return SystemLogResponse.from(repository.save(log));
    }
}
