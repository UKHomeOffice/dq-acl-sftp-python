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
      interpreter: "python",
      env: {
        PROCESS_INTERVAL: 900,
        ACL_SERVER : process.argv[5],
        ACL_USERNAME : process.argv[6],
        ACL_PASSWORD : process.argv[7],
        ACL_LANDING_DIR : process.argv[8],
        S3_BUCKET_NAME : process.argv[9],
        S3_KEY_PREFIX : process.argv[10],
        S3_ACCESS_KEY_ID : process.argv[11],
        S3_SECRET_ACCESS_KEY : process.argv[12],
        S3_REGION_NAME : "eu-west-2",
        SECONDARY_S3_BUCKET_NAME : process.argv[13],
        SECONDARY_S3_ACCESS_KEY_ID : process.argv[14],
        SECONDARY_S3_SECRET_ACCESS_KEY : process.argv[15],
        CLAMAV_URL : process.argv[16],
        CLAMAV_PORT : process.argv[17],
        ACL_RDS_HOST : process.argv[18],
        ACL_RDS_DATABASE : process.argv[19],
        ACL_RDS_USERNAME : process.argv[20],
        ACL_RDS_PASSWORD : process.argv[21],
        ACL_RDS_TABLE : process.argv[22],
        SLACK_WEBHOOK : process.argv[23]
      }
    }
  ]
};
