export default function handler(req, res) {
  res.writeHead(302, {
    Location: "http://budget01.iccnex.ovh:25589/frontpages",
  });
  res.end();
}
