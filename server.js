require('dotenv').config();

const express = require('express');
const uploadRoutes = require('./upload.routes');

const app = express();

app.use(express.json());
app.use('/api/v1', uploadRoutes);

const port = process.env.PORT || 8080;
app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});
