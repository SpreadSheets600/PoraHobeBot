export default async function handler(req, res) {
	const targetUrl = `http://dono-03.danbot.host:2521${req.url}`;

	const response = await fetch(targetUrl, {
		method: req.method,
		headers: { ...req.headers, host: "dono-03.danbot.host" },
		body: ["GET", "HEAD"].includes(req.method) ? undefined : req.body,
		redirect: "manual",
	});

	for (const [key, value] of response.headers.entries()) {
		if (!["content-encoding", "content-length", "transfer-encoding", "connection"].includes(key.toLowerCase())) {
			res.setHeader(key, value);
		}
	}

	res.status(response.status);
	const body = await response.arrayBuffer();
	res.send(Buffer.from(body));
}
