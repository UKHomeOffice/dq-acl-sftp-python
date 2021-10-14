module.exports = {
  /**
   * Application configuration
   * Note: all environment variables are required.
   *
   */
  apps : [
    {
      name      : "DQ-ACL-file-ingest",
      script    : "/ADT/bin/DQ_ACL_file_ingest",
      interpreter: "python3",
      env: {
        PROCESS_INTERVAL: 900,
        ACL_SERVER : process.argv[5],
        ACL_USERNAME : process.argv[6],
        ACL_PASSWORD : process.argv[7],
        ACL_LANDING_DIR : process.argv[8],
        S3_BUCKET_NAME : process.argv[9],
        S3_ACCESS_KEY_ID : process.argv[10],
        S3_SECRET_ACCESS_KEY : process.argv[11],
        S3_REGION_NAME : "eu-west-2",
        CLAMAV_URL : process.argv[12],
        CLAMAV_PORT : process.argv[13],
        ACL_RDS_HOST : process.argv[14],
        ACL_RDS_DATABASE : process.argv[15],
        ACL_RDS_USERNAME : process.argv[16],
        ACL_RDS_PASSWORD : process.argv[17],
        ACL_RDS_TABLE : process.argv[18],
        SLACK_WEBHOOK : process.argv[19]
      }
    }
  ]
};
