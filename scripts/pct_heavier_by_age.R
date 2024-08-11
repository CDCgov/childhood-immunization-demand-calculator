# Create data/weights.csv using CDC and WHO weight-for-age table R packages
#
# This script is included here for documentation purposes. It does not need to be
# run by an end user. Ideally, this logic could be run by r2py, rather than having
# the output data file tracked in the repo, but that is a lot of trouble.

library(tidyverse)

#' Given a vector of decreasing proportions, get the diff, applying some
#' rounding, but ensuring you add up to exactly 1.0
round_diff <- function(x, digits = 3) {
  d <- diff(c(0, x))
  d <- round(d, digits)
  # make sure they add to 1
  d[length(d)] <- 1.0 - sum(d[-length(d)])
  d <- round(d, digits)
  stopifnot(sum(d) == 1)
  d
}

# ad hoc test for round_diff
stopifnot(all(
  round_diff(c(0.12345, 0.23456, 0.34567, 0.99000)) == c(0.123, 0.111, 0.111, 0.655)
))

# WHO monthly weight-for-age using anthro package
who_month <- crossing(
  age = 0:12,
  sex = 1:2
) %>%
  mutate(
    z = anthro::anthro_zscores(
      sex = sex,
      age = age,
      is_age_in_month = TRUE,
      weight = 5.0
    )$zwei,
    # when we combine tables, we'll want all sex vars as char
    sex = as.character(sex),
    source = "WHO",
    interval = "month"
  )

# WHO weekly weight-for-age
who_week <- crossing(
  age = 0:52,
  sex = 1:2
) %>%
  mutate(
    z = anthro::anthro_zscores(
      sex = sex,
      # expects age in days
      age = age * 7,
      is_age_in_month = FALSE,
      weight = 5.0
    )$zwei,
    sex = as.character(sex),
    source = "WHO",
    interval = "week"
  )

# CDC monthly weight-for-age using childsds package
cdc_month <- crossing(
  age = 0:12,
  sex = c("female", "male"),
  weight = 5.0
) %>%
  mutate(
    z = childsds::sds(
      value = weight,
      item = "weight",
      sex = sex,
      # expects age in years
      age = age / 12,
      ref = childsds::cdc.ref
    ),
    source = "CDC",
    interval = "month"
  )

# CDC weekly weight-for-age
cdc_week <- crossing(
  age = 0:52,
  sex = c("female", "male"),
  weight = 5.0
) %>%
  mutate(
    z = childsds::sds(
      value = weight,
      item = "weight",
      sex = sex,
      # starting with weeks (0 to 52), convert to years
      # logic: weeks * (days / week) * (years / day) is years
      age = age * 7 / 365.25,
      ref = childsds::cdc.ref
    ),
    source = "CDC",
    interval = "week"
  )

# combine tables
weights <- bind_rows(
  cdc_month,
  cdc_week,
  who_month,
  who_week
) %>%
  # convert z-scores to percentiles
  mutate(p = pnorm(z)) %>%
  group_by(source, interval, age) %>%
  # take the mean percentile across the two sexes
  summarize(across(p, mean), .groups = "drop") %>%
  arrange(source, interval, age) %>%
  group_by(source, interval) %>%
  # convert cumulative percent *under* 5 kg to incident percent that hit 5 kg
  mutate(p_gt_5kg = round_diff(1 - p)) %>%
  ungroup() %>%
  select(source, interval, age, p_gt_5kg)

write_csv(weights, "data/weights.csv")
