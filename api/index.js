export const config = {
  api: {
    bodyParser: false,
  },
};

export default async function handler(req, res) {
  const targetUrl = `http://dono-03.danbot.host:2521${req.url}`;

  const getRawBody = async (req) => {
    return new Promise((resolve, reject) => {
      const chunks = [];
      req.on("data", (chunk) => chunks.push(chunk));
      req.on("end", () => resolve(Buffer.concat(chunks)));
      req.on("error", reject);
    });
  };

  const body = ["GET", "HEAD"].includes(req.method) ? undefined : await getRawBody(req);

  try {
    const response = await fetch(targetUrl, {
      method: req.method,
      headers: {
        ...req.headers,
        host: "dono-03.danbot.host",
      },
      body,
      redirect: "manual",
    });

    for (const [key, value] of response.headers.entries()) {
      if (!["content-encoding", "content-length", "transfer-encoding", "connection"].includes(key.toLowerCase())) {
        res.setHeader(key, value);
      }
    }

    res.status(response.status);
    const buffer = Buffer.from(await response.arrayBuffer());
    res.send(buffer);
  } catch (err) {
    console.error("Proxy error:", err.message);

    res.status(502).json({
      error: "Bad Gateway",
      message: "The Target Server Is Unavailabe Please Try Again Later, Or Contact SOHAM",
    });
  }
}
