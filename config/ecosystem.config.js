module.exports = {
  apps: [
    {
      name: 'cdp-backend',
      cwd: '/opt/cdp/current/backend',
      script: '.venv/bin/uvicorn',
      args: 'app.main:app --host 127.0.0.1 --port 8000 --workers 2',
      interpreter: 'none',
      env: {
        PYTHONUNBUFFERED: '1',
      },
      env_file: '/opt/cdp/current/backend/.env',
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
      out_file: '/var/log/cdp/backend.out.log',
      error_file: '/var/log/cdp/backend.err.log',
      time: true,
    },
    {
      name: 'cdp-frontend',
      cwd: '/opt/cdp/current/frontend',
      script: 'node_modules/next/dist/bin/next',
      args: 'start -p 3000',
      interpreter: 'node',
      env: {
        NODE_ENV: 'production',
        PORT: '3000',
      },
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
      out_file: '/var/log/cdp/frontend.out.log',
      error_file: '/var/log/cdp/frontend.err.log',
      time: true,
    },
  ],
};