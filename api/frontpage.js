export default function handler(req, res) {
  res.writeHead(302, {
    Location: "http://dono-03.danbot.host:2521/frontpages",
  });
  res.end();
}
