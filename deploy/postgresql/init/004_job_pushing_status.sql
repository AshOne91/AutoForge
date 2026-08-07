ALTER TABLE autoforge_generation_jobs
    DROP CONSTRAINT IF EXISTS autoforge_generation_jobs_status_check;

ALTER TABLE autoforge_generation_jobs
    ADD CONSTRAINT autoforge_generation_jobs_status_check
    CHECK (
        status IN (
            'pending',
            'generating',
            'validating',
            'committing',
            'pushing',
            'succeeded',
            'failed'
        )
    );
