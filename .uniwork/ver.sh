#!/bin/bash
# $1 = name prefix, $2 = path after /Documentation/
for v in 5.3 5.4 5.5 5.6 2017.1 2017.2 2017.3 2017.4 2018.1 2018.2 2018.3 2018.4 2019.1 2019.2 2019.3 2019.4 2020.1 2020.2 2020.3 2021.1 2021.2 2021.3 2022.1 2022.2 2022.3 2023.1 2023.2 6000.0 6000.1 6000.2 6000.3; do
  code=$(curl -sS -o /dev/null -w "%{http_code}" -m 20 -A "Mozilla/5.0" "https://docs.unity3d.com/$v/Documentation/$2")
  echo "$v $code"
done
