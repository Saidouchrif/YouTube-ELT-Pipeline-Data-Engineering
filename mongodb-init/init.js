// MongoDB initialization script
// Creates application user (if not already created) and basic collections.

db = db.getSiblingDB(process.env.MONGO_INITDB_DATABASE || 'youtube_data');

// Create collections if not exist
db.createCollection('staging_data');
db.createCollection('core_data');
db.createCollection('history_data');

// Indexes
db.getCollection('staging_data').createIndex({ video_id: 1 }, { unique: true, name: 'ux_staging_video' });
db.getCollection('core_data').createIndex({ video_id: 1 }, { unique: true, name: 'ux_core_video' });
db.getCollection('history_data').createIndex({ video_id: 1, valid_from: 1 }, { name: 'ix_hist_video_from' });
